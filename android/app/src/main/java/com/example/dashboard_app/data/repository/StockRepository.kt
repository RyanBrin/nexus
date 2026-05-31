package com.example.dashboard_app.data.repository

import com.example.dashboard_app.data.db.StockDao
import com.example.dashboard_app.data.model.StockItem
import com.example.dashboard_app.data.network.AlphaVantageService
import kotlinx.coroutines.flow.Flow

class StockRepository(
    private val dao: StockDao,
    private val api: AlphaVantageService = AlphaVantageService.create()
) {
    val stocks: Flow<List<StockItem>> = dao.getAll()

    suspend fun save(stock: StockItem) = dao.upsert(stock)
    suspend fun delete(stock: StockItem) = dao.delete(stock)

    // Fetches a live price for one ticker and updates the DB row.
    // Returns true on success, false if rate-limited or network error.
    suspend fun refreshPrice(stock: StockItem, apiKey: String): Boolean {
        return try {
            val response = api.getQuote(symbol = stock.ticker, apiKey = apiKey)
            val quote = response.globalQuote
            // Alpha Vantage returns a Note field when rate-limited
            if (response.note != null || response.information != null || quote == null) return false
            val price = quote.price.toDoubleOrNull() ?: return false
            dao.upsert(
                stock.copy(
                    price = price,
                    changePercent = quote.changePercent.trimEnd('%'),
                    lastUpdated = System.currentTimeMillis()
                )
            )
            true
        } catch (e: Exception) {
            false
        }
    }
}
