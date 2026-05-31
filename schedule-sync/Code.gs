const CONFIG = {
  TARGET_CALENDAR_ID:
    "e6c9b1a3ecf87deb25df7e20afcb2c15b6c215f2a05a3472119ad5d377df52ce@group.calendar.google.com",

  RESULT_EMAIL:
    "ryanjmaesbrinkman@gmail.com",

  PEBBLE_SOURCE_CALENDAR_ID:
    "pebblecreekschedule@gmail.com",

  PEBBLE_EVENT_TITLE:
    "Ryan - Pebble Creek Golf Course",

  PEBBLE_TRIGGER_LABEL_NAME:
    "PebbleSyncTrigger",

  PEBBLE_PROCESSED_LABEL_NAME:
    "PebbleSyncProcessed",

  PEBBLE_EMAIL_FROM:
    "pebblecreekschedule@gmail.com",

  // Shift times by type — detected from source event title/description.
  PEBBLE_SHIFTS: {
    closing:  { startHour: 14, startMinute: 30, endHour: 21, endMinute: 30 },
    opening:  { startHour:  6, startMinute: 30, endHour: 14, endMinute: 30 },
    float:    { startHour: 10, startMinute:  0, endHour: 18, endMinute:  0 },
    // Fallback if no keyword matched.
    default:  { startHour: 14, startMinute: 30, endHour: 21, endMinute: 30 }
  },

  BESTBUY_SCREENSHOT_FOLDER_NAME:
    "BestBuyScheduleScreenshots",

  BESTBUY_EVENT_BASE_TITLE:
    "Ryan - Best Buy",

  BESTBUY_LOCATION:
    "#1012 Bismarck ND",

  DELETE_BESTBUY_SCREENSHOTS_AFTER_SUCCESS:
    false,

  // Script property key used to track which Drive file IDs have already been processed.
  PROCESSED_FILES_PROPERTY_KEY:
    "processedBestBuyFileIds",

  // Store this in Apps Script project settings:
  // Project Settings → Script Properties → ANTHROPIC_API_KEY
  ANTHROPIC_API_KEY:
    PropertiesService.getScriptProperties().getProperty("ANTHROPIC_API_KEY") || ""
};

// Shifts more than 60 days in the past or 180 days in the future are flagged.
const SHIFT_DATE_MIN_DAYS = -60;
const SHIFT_DATE_MAX_DAYS = 180;

/**
 * Run this manually if you want to sync everything right now.
 */
function runFullWorkScheduleSync() {
  const pebbleResult = syncPebbleCreekToFamilyCalendar();
  const bestBuyResult = importBestBuyScreenshotsToCalendar();
  sendFullSyncResultEmail(pebbleResult, bestBuyResult, "Manual/full sync");
}

/**
 * Use this for the time-based trigger (every 1-5 minutes).
 * Only runs the full sync when a new Pebble Creek email is found.
 */
function checkPebbleCreekEmailsThenSync() {
  const triggerResult = getNewPebbleCalendarUpdateThreads();
  if (triggerResult.threads.length === 0) return;
  markPebbleThreadsProcessed(triggerResult.threads);
  const pebbleResult = syncPebbleCreekToFamilyCalendar();
  const bestBuyResult = importBestBuyScreenshotsToCalendar();
  sendFullSyncResultEmail(
    pebbleResult,
    bestBuyResult,
    "Triggered by Pebble Creek calendar email: " + triggerResult.threads.length + " new thread(s)"
  );
}

function runWhenPebbleCalendarEmailArrives() {
  checkPebbleCreekEmailsThenSync();
}

/************************************************
 * GMAIL EMAIL TRIGGER CHECK
 ************************************************/

function getNewPebbleCalendarUpdateThreads() {
  const triggerLabel = getOrCreateGmailLabel(CONFIG.PEBBLE_TRIGGER_LABEL_NAME);
  const processedLabel = getOrCreateGmailLabel(CONFIG.PEBBLE_PROCESSED_LABEL_NAME);
  const query =
    'label:' + CONFIG.PEBBLE_TRIGGER_LABEL_NAME +
    ' -label:' + CONFIG.PEBBLE_PROCESSED_LABEL_NAME +
    ' from:' + CONFIG.PEBBLE_EMAIL_FROM +
    ' newer_than:30d';
  const threads = GmailApp.search(query, 0, 10);
  return { triggerLabel, processedLabel, query, threads };
}

function markPebbleThreadsProcessed(threads) {
  const processedLabel = getOrCreateGmailLabel(CONFIG.PEBBLE_PROCESSED_LABEL_NAME);
  threads.forEach(thread => { processedLabel.addToThread(thread); });
}

function getOrCreateGmailLabel(name) {
  let label = GmailApp.getUserLabelByName(name);
  if (!label) label = GmailApp.createLabel(name);
  return label;
}

/************************************************
 * PEBBLE CREEK CALENDAR SYNC
 ************************************************/

function syncPebbleCreekToFamilyCalendar() {
  const sourceCalendar = CalendarApp.getCalendarById(CONFIG.PEBBLE_SOURCE_CALENDAR_ID);
  const targetCalendar = CalendarApp.getCalendarById(CONFIG.TARGET_CALENDAR_ID);

  if (!sourceCalendar) throw new Error("Pebble Creek source calendar not found.");
  if (!targetCalendar) throw new Error("Target calendar not found.");

  const past = new Date();
  past.setDate(past.getDate() - 7);
  past.setHours(0, 0, 0, 0);

  const future = new Date();
  future.setDate(future.getDate() + 30);
  future.setHours(23, 59, 59, 999);

  const sourceEvents = sourceCalendar.getEvents(past, future);

  let checkedCount = 0, skippedCount = 0, createdCount = 0, updatedCount = 0, removedCount = 0;
  const createdEvents = [], updatedEvents = [], removedEvents = [], skippedEvents = [];

  sourceEvents.forEach(sourceEvent => {
    checkedCount++;

    const title = sourceEvent.getTitle() || "";
    const description = sourceEvent.getDescription() || "";
    const location = sourceEvent.getLocation() || "";
    const sourceId = sourceEvent.getId();
    const sourceStart = sourceEvent.getStartTime();
    const sourceEnd = sourceEvent.getEndTime();

    const fullText = (title + " " + description + " " + location).toLowerCase();
    const tag = "PEBBLE_SYNC_ID:" + sourceId;

    const syncedEventsForSource = findPebbleSyncedEventsForSource(targetCalendar, sourceStart, tag);

    if (!fullText.includes("ryan")) {
      if (syncedEventsForSource.length > 0) {
        syncedEventsForSource.forEach(event => {
          removedEvents.push(
            formatDateLine(event.getStartTime(), event.getEndTime()) +
            " | removed because source event no longer mentions Ryan | source title: " + title
          );
          event.deleteEvent();
          removedCount++;
        });
      } else {
        skippedEvents.push(title || "Untitled Pebble event");
      }
      skippedCount++;
      return;
    }

    // Detect shift type from title + description, apply hardcoded times.
    const shiftText = (title + " " + description).toLowerCase();
    let shiftType = "default";
    if (shiftText.includes("open")) shiftType = "opening";
    else if (shiftText.includes("float")) shiftType = "float";
    else if (shiftText.includes("close") || shiftText.includes("closing")) shiftType = "closing";

    const times = CONFIG.PEBBLE_SHIFTS[shiftType];
    const start = new Date(sourceStart);
    start.setHours(times.startHour, times.startMinute, 0, 0);
    const end = new Date(sourceStart);
    end.setHours(times.endHour, times.endMinute, 0, 0);

    const eventDescription =
      "Auto-synced from Pebble Creek\n\nOriginal event: " + title + "\nShift type: " + shiftType + "\n\n" + tag;

    if (syncedEventsForSource.length > 0) {
      const existing = syncedEventsForSource[0];
      existing.setTitle(CONFIG.PEBBLE_EVENT_TITLE);
      existing.setTime(start, end);
      existing.setDescription(eventDescription);
      updatedCount++;
      updatedEvents.push(formatDateLine(start, end) + " | source title: " + title);
      return;
    }

    targetCalendar.createEvent(CONFIG.PEBBLE_EVENT_TITLE, start, end, {
      description: eventDescription
    });
    createdCount++;
    createdEvents.push(formatDateLine(start, end) + " | source title: " + title);
  });

  return {
    checkedCount, skippedCount, createdCount, updatedCount, removedCount,
    createdEvents, updatedEvents, removedEvents, skippedEvents,
    startRange: past, endRange: future
  };
}

function findPebbleSyncedEventsForSource(targetCalendar, sourceStart, tag) {
  return targetCalendar.getEventsForDay(sourceStart).filter(event => {
    return (event.getDescription() || "").includes(tag);
  });
}

/************************************************
 * BEST BUY — PROCESSED FILE TRACKING
 ************************************************/

function getProcessedFileIds() {
  const raw = PropertiesService.getScriptProperties().getProperty(CONFIG.PROCESSED_FILES_PROPERTY_KEY);
  if (!raw) return {};
  try { return JSON.parse(raw); } catch (e) { return {}; }
}

function markFileProcessed(fileId, fileName) {
  const processed = getProcessedFileIds();
  processed[fileId] = { fileName, processedAt: new Date().toISOString() };
  PropertiesService.getScriptProperties().setProperty(
    CONFIG.PROCESSED_FILES_PROPERTY_KEY,
    JSON.stringify(processed)
  );
}

function isFileProcessed(fileId) {
  return !!getProcessedFileIds()[fileId];
}

/**
 * Run this manually to reset the processed-files log,
 * forcing all screenshots to be re-parsed on the next sync.
 */
function resetProcessedBestBuyFiles() {
  PropertiesService.getScriptProperties().deleteProperty(CONFIG.PROCESSED_FILES_PROPERTY_KEY);
  Logger.log("Processed Best Buy file log cleared.");
}

/************************************************
 * BEST BUY — IMPORT
 ************************************************/

function importBestBuyScreenshotsToCalendar() {
  const folderIterator = DriveApp.getFoldersByName(CONFIG.BESTBUY_SCREENSHOT_FOLDER_NAME);

  if (!folderIterator.hasNext()) {
    return {
      checkedFiles: 0, createdEvents: [], updatedEvents: [],
      skippedEvents: ["Folder not found: " + CONFIG.BESTBUY_SCREENSHOT_FOLDER_NAME],
      reviewNotes: [], rawOcrTexts: []
    };
  }

  const folder = folderIterator.next();
  const files = folder.getFiles();
  const calendar = CalendarApp.getCalendarById(CONFIG.TARGET_CALENDAR_ID);
  if (!calendar) throw new Error("Target calendar not found.");

  let checkedFiles = 0;
  const createdEvents = [], updatedEvents = [], skippedEvents = [], reviewNotes = [], rawOcrTexts = [];

  while (files.hasNext()) {
    const file = files.next();
    checkedFiles++;

    // Skip files that have already been successfully processed.
    if (isFileProcessed(file.getId())) {
      skippedEvents.push("Already processed (skipped): " + file.getName());
      continue;
    }

    try {
      const text = ocrImageToText(file);
      rawOcrTexts.push("FILE: " + file.getName() + "\n\n" + text);

      const parseResult = parseBestBuyShifts(text);
      const shifts = parseResult.shifts;
      reviewNotes.push(...parseResult.reviewNotes);

      if (shifts.length === 0) {
        skippedEvents.push("No shifts found in " + file.getName());
        // Don't mark as processed — let the user fix the screenshot and retry.
        continue;
      }

      shifts.forEach(shift => {
        const title = CONFIG.BESTBUY_EVENT_BASE_TITLE + " - " + shift.job;
        const tag = "BESTBUY_SHIFT:" + shift.dateKey + "_" + shift.startKey + "_" + shift.endKey;
        const description =
          "Auto-imported from Best Buy screenshot\n\n" +
          "Role: " + shift.job + "\n" +
          "Store: " + CONFIG.BESTBUY_LOCATION + "\n" +
          "Shift: " + shift.label + "\n\n" + tag;

        // Match by tag in description — immune to time-parsing drift.
        const sameDayEvents = calendar.getEventsForDay(shift.start);
        const matchingEvent = sameDayEvents.find(event => {
          const desc = event.getDescription() || "";
          const looksBestBuy =
            (event.getTitle() || "").includes("Best Buy") ||
            desc.includes("BESTBUY_SHIFT") ||
            desc.includes("BESTBUY_SYNC");
          return looksBestBuy && desc.includes(tag);
        });

        if (matchingEvent) {
          matchingEvent.setTitle(title);
          matchingEvent.setTime(shift.start, shift.end);
          matchingEvent.setLocation(CONFIG.BESTBUY_LOCATION);
          matchingEvent.setDescription(description);
          updatedEvents.push(shift.label + " | " + shift.job);
          return;
        }

        calendar.createEvent(title, shift.start, shift.end, {
          location: CONFIG.BESTBUY_LOCATION,
          description: description
        });
        createdEvents.push(shift.label + " | " + shift.job);
      });

      // Mark processed only after all shifts have been written successfully.
      markFileProcessed(file.getId(), file.getName());

      if (CONFIG.DELETE_BESTBUY_SCREENSHOTS_AFTER_SUCCESS) file.setTrashed(true);

    } catch (err) {
      skippedEvents.push("ERROR with " + file.getName() + ": " + err.message);
    }
  }

  return { checkedFiles, createdEvents, updatedEvents, skippedEvents, reviewNotes, rawOcrTexts };
}

function ocrImageToText(file) {
  const blob = file.getBlob();
  const resource = { name: "OCR_" + file.getName(), mimeType: MimeType.GOOGLE_DOCS };
  const ocrFile = Drive.Files.create(resource, blob, { ocr: true, ocrLanguage: "en" });
  const doc = DocumentApp.openById(ocrFile.id);
  const text = doc.getBody().getText();
  DriveApp.getFileById(ocrFile.id).setTrashed(true);
  return text;
}

/************************************************
 * BEST BUY — CLAUDE PARSING
 ************************************************/

function parseBestBuyShifts(text) {
  const today = new Date();

  const prompt =
    "You are a work schedule parser. Extract all shifts from this OCR text of a Best Buy schedule screenshot.\n\n" +
    "Today's date is " + Utilities.formatDate(today, Session.getScriptTimeZone(), "MMMM d, yyyy") + ".\n\n" +
    "Return ONLY a valid JSON object in exactly this format, no explanation:\n" +
    '{\n  "reviewNotes": [],\n  "shifts": [\n    {\n' +
    '      "year": 2026,\n      "month": 5,\n      "day": 31,\n' +
    '      "startHour": 11,\n      "startMinute": 0,\n' +
    '      "endHour": 19,\n      "endMinute": 0,\n' +
    '      "job": "Host"\n    }\n  ]\n}\n\n' +
    "Rules:\n" +
    "- Use 24-hour time (14 for 2pm, 22 for 10pm)\n" +
    "- month is 1-12 (not 0-indexed)\n" +
    "- If end time is before start time, the shift ends the next day\n" +
    "- job should be the role name from inside parentheses e.g. 'Host (Host)' → 'Host', 'Product Flow (Daily Tasks)' → 'Product Flow'\n" +
    "- Include ALL shifts shown — this is Ryan's personal schedule so every shift listed is his\n" +
    "- The schedule is a weekly calendar grid. Days appear as column headers (Sun, Mon, Tue etc) with a date number. Shifts appear below the day they belong to.\n" +
    "- A time like '11:00a - 7:00p' below 'Fri 30' means a shift on that Friday the 30th\n" +
    "- If the month or year is ambiguous, use the most recently passed or upcoming date that makes sense\n" +
    "- The store location '#1012 Bismarck ND' is not a shift — ignore it\n\n" +
    "OCR TEXT:\n" + text;

  const response = UrlFetchApp.fetch("https://api.anthropic.com/v1/messages", {
    method: "post",
    contentType: "application/json",
    headers: {
      "x-api-key": CONFIG.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01"
    },
    payload: JSON.stringify({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 1024,
      messages: [{ role: "user", content: prompt }]
    }),
    muteHttpExceptions: true
  });

  const raw = JSON.parse(response.getContentText());

  if (!raw.content || !raw.content[0]) {
    return { shifts: [], reviewNotes: ["Claude API call failed: " + response.getContentText()] };
  }

  let parsed;
  try {
    const jsonText = raw.content[0].text.trim().replace(/^```json|^```|```$/gm, "").trim();
    parsed = JSON.parse(jsonText);
  } catch (e) {
    return { shifts: [], reviewNotes: ["Failed to parse Claude response: " + raw.content[0].text] };
  }

  const now = new Date();
  const minDate = new Date(now);
  minDate.setDate(minDate.getDate() + SHIFT_DATE_MIN_DAYS);
  const maxDate = new Date(now);
  maxDate.setDate(maxDate.getDate() + SHIFT_DATE_MAX_DAYS);

  const reviewNotes = parsed.reviewNotes || [];
  const shifts = [];

  (parsed.shifts || []).forEach(s => {
    const start = new Date(s.year, s.month - 1, s.day, s.startHour, s.startMinute, 0);
    const end   = new Date(s.year, s.month - 1, s.day, s.endHour,   s.endMinute,   0);

    if (end <= start) end.setDate(end.getDate() + 1);

    // Validate date is within reasonable range.
    if (start < minDate || start > maxDate) {
      reviewNotes.push(
        "Shift date out of expected range and was skipped: " +
        Utilities.formatDate(start, Session.getScriptTimeZone(), "EEE MMM d yyyy") +
        " | job: " + (s.job || "?")
      );
      return;
    }

    const job = s.job || "Best Buy Shift";

    shifts.push({
      start, end, job,
      dateKey:  Utilities.formatDate(start, Session.getScriptTimeZone(), "yyyy_MM_dd"),
      startKey: Utilities.formatDate(start, Session.getScriptTimeZone(), "HHmm"),
      endKey:   Utilities.formatDate(end,   Session.getScriptTimeZone(), "HHmm"),
      label:    formatDateLine(start, end)
    });
  });

  return { shifts, reviewNotes };
}

/************************************************
 * EMAIL REPORT
 ************************************************/

function sendFullSyncResultEmail(pebble, bestBuy, triggerReason) {
  const now = new Date();
  const ranAt = Utilities.formatDate(now, Session.getScriptTimeZone(), "EEE MMM d, yyyy 'at' h:mm a z");

  // Build a quick summary for the subject line
  const totalNew = pebble.createdCount + pebble.updatedCount + bestBuy.createdEvents.length + bestBuy.updatedEvents.length;
  const hasErrors = bestBuy.skippedEvents.some(s => s.startsWith("ERROR")) || bestBuy.reviewNotes.length > 0;
  const subjectTag = hasErrors ? "⚠️ needs review" : totalNew > 0 ? "✓ " + totalNew + " change(s)" : "✓ no changes";
  const subject = "Work Schedule Sync — " + subjectTag + " — " + Utilities.formatDate(now, Session.getScriptTimeZone(), "MMM d");

  const sep  = "─".repeat(50);
  const sep2 = "━".repeat(50);

  let body = "";
  body += "WORK SCHEDULE SYNC REPORT\n";
  body += sep2 + "\n";
  body += "Ran at:  " + ranAt + "\n";
  body += "Trigger: " + triggerReason + "\n";
  body += sep2 + "\n\n";

  // ── PEBBLE CREEK ──
  body += "PEBBLE CREEK GOLF COURSE\n" + sep + "\n";
  body += "Scanned: " + Utilities.formatDate(pebble.startRange, Session.getScriptTimeZone(), "MMM d") +
          " → " + Utilities.formatDate(pebble.endRange, Session.getScriptTimeZone(), "MMM d, yyyy") + "\n";
  body += "Events scanned: " + pebble.checkedCount +
          "  |  yours: " + (pebble.checkedCount - pebble.skippedCount) +
          "  |  skipped (not yours): " + pebble.skippedCount + "\n\n";

  if (pebble.createdCount === 0 && pebble.updatedCount === 0 && pebble.removedCount === 0) {
    body += "  No changes — calendar is already up to date.\n";
  }

  if (pebble.createdEvents.length) {
    body += "  ✚ ADDED (" + pebble.createdCount + ")\n";
    pebble.createdEvents.forEach(e => { body += "    • " + e + "\n"; });
    body += "\n";
  }

  if (pebble.updatedEvents.length) {
    body += "  ✎ UPDATED (" + pebble.updatedCount + ")\n";
    pebble.updatedEvents.forEach(e => { body += "    • " + e + "\n"; });
    body += "\n";
  }

  if (pebble.removedEvents.length) {
    body += "  ✖ REMOVED (" + pebble.removedCount + ")\n";
    pebble.removedEvents.forEach(e => { body += "    • " + e + "\n"; });
    body += "\n";
  }

  // ── BEST BUY ──
  body += "\nBEST BUY #1012 BISMARCK\n" + sep + "\n";
  body += "Screenshots scanned: " + bestBuy.checkedFiles + "\n\n";

  if (bestBuy.createdEvents.length === 0 && bestBuy.updatedEvents.length === 0 &&
      !bestBuy.skippedEvents.some(s => !s.startsWith("Already processed"))) {
    body += "  No new shifts found.\n";
  }

  if (bestBuy.createdEvents.length) {
    body += "  ✚ ADDED (" + bestBuy.createdEvents.length + ")\n";
    bestBuy.createdEvents.forEach(e => { body += "    • " + e + "\n"; });
    body += "\n";
  }

  if (bestBuy.updatedEvents.length) {
    body += "  ✎ UPDATED (" + bestBuy.updatedEvents.length + ")\n";
    bestBuy.updatedEvents.forEach(e => { body += "    • " + e + "\n"; });
    body += "\n";
  }

  // Separate real errors from "already processed" skips
  const errors = bestBuy.skippedEvents.filter(s => !s.startsWith("Already processed"));
  const alreadyDone = bestBuy.skippedEvents.filter(s => s.startsWith("Already processed"));

  if (errors.length) {
    body += "  ⚠ ERRORS / SKIPPED\n";
    errors.forEach(e => { body += "    • " + e + "\n"; });
    body += "\n";
  }

  if (alreadyDone.length) {
    body += "  ↩ Already processed (skipped): " + alreadyDone.length + " file(s)\n\n";
  }

  if (bestBuy.reviewNotes.length) {
    body += "  ⚠ NEEDS REVIEW\n";
    bestBuy.reviewNotes.forEach(n => { body += "    • " + n + "\n"; });
    body += "\n";
  }

  // Raw OCR — only include if there were errors or new shifts
  if (bestBuy.rawOcrTexts.length && (errors.length || bestBuy.reviewNotes.length || bestBuy.createdEvents.length)) {
    body += "\n" + sep + "\nRAW OCR OUTPUT (for debugging)\n" + sep + "\n";
    body += bestBuy.rawOcrTexts.join("\n\n" + sep + "\n\n");
  }

  body += "\n\n" + sep2 + "\n";
  body += "Next sync runs automatically when a Pebble Creek email arrives,\n";
  body += "or add screenshots to BestBuyScheduleScreenshots in Drive.\n";

  MailApp.sendEmail(CONFIG.RESULT_EMAIL, subject, body);
}

/************************************************
 * HELPERS
 ************************************************/

function formatDateLine(start, end) {
  return (
    Utilities.formatDate(start, Session.getScriptTimeZone(), "EEE MMM d yyyy h:mm a") +
    " -> " +
    Utilities.formatDate(end, Session.getScriptTimeZone(), "h:mm a")
  );
}
