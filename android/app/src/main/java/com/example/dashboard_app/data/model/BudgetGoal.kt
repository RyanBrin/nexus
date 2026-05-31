package com.example.dashboard_app.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "budget_goals")
data class BudgetGoal(
    @PrimaryKey val category: String,
    val monthlyCapDollars: Double,
    val emoji: String = ""
)
