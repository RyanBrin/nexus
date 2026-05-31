package com.example.dashboard_app.ui.shifts

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.dashboard_app.data.db.AppDatabase
import com.example.dashboard_app.data.model.WorkShift
import com.example.dashboard_app.data.repository.ShiftsRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class ShiftsViewModel(app: Application) : AndroidViewModel(app) {
    private val repo = ShiftsRepository(AppDatabase.getInstance(app).workShiftDao())

    val shifts = repo.shifts.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun save(id: Int, employer: String, title: String, startTime: Long, endTime: Long, notes: String) {
        viewModelScope.launch {
            repo.save(WorkShift(id, employer, title, startTime, endTime, notes))
        }
    }

    fun delete(shift: WorkShift) {
        viewModelScope.launch { repo.delete(shift) }
    }
}
