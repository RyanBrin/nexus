package com.example.dashboard_app.data.db

import androidx.room.*
import com.example.dashboard_app.data.model.BudgetGoal
import kotlinx.coroutines.flow.Flow

@Dao
interface BudgetGoalDao {
    @Query("SELECT * FROM budget_goals ORDER BY category ASC")
    fun getAll(): Flow<List<BudgetGoal>>

    @Upsert
    suspend fun upsert(goal: BudgetGoal)

    @Delete
    suspend fun delete(goal: BudgetGoal)
}
