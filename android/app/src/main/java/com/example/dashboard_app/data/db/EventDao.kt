package com.example.dashboard_app.data.db

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Query
import androidx.room.Upsert
import com.example.dashboard_app.data.model.Event
import kotlinx.coroutines.flow.Flow

/**
 * Data Access Object — every DB operation the app needs for events.
 * Room generates the implementation at compile time (via KSP).
 */
@Dao
interface EventDao {

    /** Reactive stream of all events, soonest first. Emits again whenever the table changes. */
    @Query("SELECT * FROM events ORDER BY dateTime ASC")
    fun getAllEvents(): Flow<List<Event>>

    /** Insert if new (id == 0) or update if it already exists. */
    @Upsert
    suspend fun upsert(event: Event)

    @Delete
    suspend fun delete(event: Event)
}
