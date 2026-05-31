package com.example.dashboard_app.ui.budget

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.dashboard_app.data.db.AppDatabase
import com.example.dashboard_app.data.model.BudgetGoal
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

val DEFAULT_GOALS = listOf(
    BudgetGoal("Food / Drinks",              140.00, "🍔"),
    BudgetGoal("Gas / Car",                  170.00, "⛽"),
    BudgetGoal("Shopping / Lifestyle",       232.00, "🛍️"),
    BudgetGoal("Tech / Best Buy",            100.00, "💻"),
    BudgetGoal("Apps / Subscriptions",        20.00, "📱"),
    BudgetGoal("Transfers / Unclear",        100.00, "💸"),
    BudgetGoal("Entertainment",               50.00, "🎮"),
    BudgetGoal("Other",                       50.00, "📦"),
)

class BudgetGoalViewModel(app: Application) : AndroidViewModel(app) {
    private val dao = AppDatabase.getInstance(app).budgetGoalDao()

    val goals = dao.getAll().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun save(goal: BudgetGoal) = viewModelScope.launch { dao.upsert(goal) }
    fun delete(goal: BudgetGoal) = viewModelScope.launch { dao.delete(goal) }

    fun seedDefaults() = viewModelScope.launch {
        if (goals.value.isEmpty()) {
            DEFAULT_GOALS.forEach { dao.upsert(it) }
        }
    }
}
