package com.example.dashboard_app.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "stocks")
data class StockItem(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val ticker: String,
    val companyName: String = "",
    val price: Double = 0.0,
    val shares: Double = 0.0,
    val changePercent: String = "",   // e.g. "+1.42%" — from live API
    val lastUpdated: Long = 0L        // epoch ms of last successful price fetch
)
