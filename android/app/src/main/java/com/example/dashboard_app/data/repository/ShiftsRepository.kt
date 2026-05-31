package com.example.dashboard_app.data.repository

import com.example.dashboard_app.data.db.WorkShiftDao
import com.example.dashboard_app.data.model.WorkShift

class ShiftsRepository(private val dao: WorkShiftDao) {
    val shifts = dao.getAll()

    suspend fun save(shift: WorkShift) = dao.upsert(shift)
    suspend fun delete(shift: WorkShift) = dao.delete(shift)
}
