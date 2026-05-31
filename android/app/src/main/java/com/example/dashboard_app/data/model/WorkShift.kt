package com.example.dashboard_app.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "work_shifts")
data class WorkShift(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val employer: String,       // "Pebble Creek" or "Best Buy"
    val title: String,          // "Closing", "Opening", "Float", "Product Flow", etc.
    val startTime: Long,        // epoch ms
    val endTime: Long,          // epoch ms
    val notes: String = ""
)
