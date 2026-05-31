package com.example.dashboard_app.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * A single calendar event.
 *
 * @param id        Auto-generated primary key. Leave as 0 to CREATE a new event;
 *                  Room assigns the real id. Pass the real id back to UPDATE an event.
 * @param title     Event title (required — validated in the UI).
 * @param dateTime  When the event happens, stored as Unix epoch MILLISECONDS.
 *                  Storing a Long keeps DB sorting trivial.
 * @param notes     Optional free-text notes.
 */
@Entity(tableName = "events")
data class Event(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val title: String,
    val dateTime: Long,
    val notes: String = ""
)
