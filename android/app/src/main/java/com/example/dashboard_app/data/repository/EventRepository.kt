package com.example.dashboard_app.data.repository

import com.example.dashboard_app.data.db.EventDao
import com.example.dashboard_app.data.model.Event
import kotlinx.coroutines.flow.Flow

/**
 * Repository = the single source of truth the rest of the app talks to.
 * Right now it just forwards to the DAO, but this is where you'll later add
 * caching, network calls (Phase 2 stock prices), or merging multiple sources.
 */
class EventRepository(private val dao: EventDao) {
    val events: Flow<List<Event>> = dao.getAllEvents()
    suspend fun save(event: Event) = dao.upsert(event)
    suspend fun delete(event: Event) = dao.delete(event)
}
