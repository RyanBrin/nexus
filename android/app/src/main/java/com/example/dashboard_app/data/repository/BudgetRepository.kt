package com.example.dashboard_app.data.repository

import com.example.dashboard_app.data.db.CreditCardDao
import com.example.dashboard_app.data.db.TransactionDao
import com.example.dashboard_app.data.model.CreditCard
import com.example.dashboard_app.data.model.Transaction
import kotlinx.coroutines.flow.Flow

class BudgetRepository(
    private val transactionDao: TransactionDao,
    private val creditCardDao: CreditCardDao
) {
    val transactions: Flow<List<Transaction>> = transactionDao.getAll()
    val creditCards: Flow<List<CreditCard>> = creditCardDao.getAll()

    suspend fun save(transaction: Transaction) = transactionDao.upsert(transaction)
    suspend fun delete(transaction: Transaction) = transactionDao.delete(transaction)

    suspend fun save(card: CreditCard) = creditCardDao.upsert(card)
    suspend fun delete(card: CreditCard) = creditCardDao.delete(card)
}
