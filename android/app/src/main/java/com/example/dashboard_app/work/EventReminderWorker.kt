package com.example.dashboard_app.work

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import androidx.core.app.NotificationCompat
import androidx.work.*
import com.example.dashboard_app.data.db.AppDatabase
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.flow.first

class EventReminderWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {

    override suspend fun doWork(): Result {
        val context = applicationContext
        val db = AppDatabase.getInstance(context)

        val now = System.currentTimeMillis()
        val windowStart = now
        val windowEnd = now + 60 * 60 * 1000L  // 1 hour from now

        val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        ensureChannel(nm)

        // Check calendar events
        val events = db.eventDao().getAllEvents().first()
        events.filter { it.dateTime in windowStart..windowEnd }.forEachIndexed { i, event ->
            val minsUntil = ((event.dateTime - now) / 60_000).toInt().coerceAtLeast(0)
            nm.notify(1000 + i, NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("📅 ${event.title}")
                .setContentText(if (minsUntil == 0) "Starting now" else "Starting in $minsUntil min")
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .build())
        }

        // Check work shifts
        val shifts = db.workShiftDao().getAll().first()
        shifts.filter { it.startTime in windowStart..windowEnd }.forEachIndexed { i, shift ->
            val minsUntil = ((shift.startTime - now) / 60_000).toInt().coerceAtLeast(0)
            nm.notify(2000 + i, NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("💼 ${shift.employer} — ${shift.title}")
                .setContentText(if (minsUntil == 0) "Starting now" else "Starting in $minsUntil min")
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .build())
        }

        return Result.success()
    }

    private fun ensureChannel(nm: NotificationManager) {
        if (nm.getNotificationChannel(CHANNEL_ID) == null) {
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "Reminders", NotificationManager.IMPORTANCE_HIGH).apply {
                    description = "Upcoming event and shift reminders"
                }
            )
        }
    }

    companion object {
        const val CHANNEL_ID = "dashboard_reminders"
        private const val WORK_NAME = "event_reminder"

        fun schedule(context: Context) {
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                PeriodicWorkRequestBuilder<EventReminderWorker>(15, TimeUnit.MINUTES)
                    .setConstraints(Constraints.Builder().build())
                    .build()
            )
        }
    }
}
