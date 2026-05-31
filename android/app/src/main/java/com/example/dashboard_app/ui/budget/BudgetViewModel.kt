package com.example.dashboard_app.ui.budget

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.dashboard_app.data.db.AppDatabase
import com.example.dashboard_app.data.model.CreditCard
import com.example.dashboard_app.data.model.Transaction
import com.example.dashboard_app.data.repository.BudgetRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class BudgetViewModel(app: Application) : AndroidViewModel(app) {

    private val repo = BudgetRepository(
        AppDatabase.getInstance(app).transactionDao(),
        AppDatabase.getInstance(app).creditCardDao()
    )

    val transactions: StateFlow<List<Transaction>> = repo.transactions
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val creditCards: StateFlow<List<CreditCard>> = repo.creditCards
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun saveTransaction(id: Int, description: String, amount: Double, category: String, date: Long) {
        viewModelScope.launch {
            repo.save(Transaction(id = id, description = description.trim(), amount = amount, category = category, date = date))
        }
    }

    fun deleteTransaction(transaction: Transaction) {
        viewModelScope.launch { repo.delete(transaction) }
    }

    fun saveCreditCard(id: Int, name: String, balance: Double, limit: Double) {
        viewModelScope.launch {
            repo.save(CreditCard(id = id, name = name.trim(), balance = balance, limit = limit))
        }
    }

    fun deleteCreditCard(card: CreditCard) {
        viewModelScope.launch { repo.delete(card) }
    }
}
