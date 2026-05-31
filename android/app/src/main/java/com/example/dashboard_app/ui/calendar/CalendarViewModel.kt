package com.example.dashboard_app.ui.calendar

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.dashboard_app.data.db.AppDatabase
import com.example.dashboard_app.data.model.Event
import com.example.dashboard_app.data.repository.EventRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * Holds and exposes the calendar UI state, and survives screen rotations.
 *
 * Extends AndroidViewModel so the default `viewModel()` factory can construct it
 * (it needs the Application to build the database) — no custom factory required.
 * For a bigger app you'd swap this for Hilt dependency injection later.
 */
class CalendarViewModel(app: Application) : AndroidViewModel(app) {

    private val repo = EventRepository(AppDatabase.getInstance(app).eventDao())

    /** The DB Flow turned into a lifecycle-aware StateFlow the UI can collect. */
    val events: StateFlow<List<Event>> = repo.events
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    /** Create (id = 0) or update (real id) an event. Title/notes are trimmed here. */
    fun saveEvent(id: Int, title: String, dateTime: Long, notes: String) {
        viewModelScope.launch {
            repo.save(Event(id = id, title = title.trim(), dateTime = dateTime, notes = notes.trim()))
        }
    }

    fun deleteEvent(event: Event) {
        viewModelScope.launch { repo.delete(event) }
    }
}
