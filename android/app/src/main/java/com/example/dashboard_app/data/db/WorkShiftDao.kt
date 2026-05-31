package com.example.dashboard_app.data.db

import androidx.room.*
import com.example.dashboard_app.data.model.WorkShift
import kotlinx.coroutines.flow.Flow

@Dao
interface WorkShiftDao {
    @Query("SELECT * FROM work_shifts ORDER BY startTime ASC")
    fun getAll(): Flow<List<WorkShift>>

    @Upsert
    suspend fun upsert(shift: WorkShift)

    @Delete
    suspend fun delete(shift: WorkShift)
}
