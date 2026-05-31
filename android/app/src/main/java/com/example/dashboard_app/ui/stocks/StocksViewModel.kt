package com.example.dashboard_app.ui.stocks

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.dashboard_app.BuildConfig
import com.example.dashboard_app.data.db.AppDatabase
import com.example.dashboard_app.ui.settings.PREF_ALPHA_VANTAGE_KEY
import com.example.dashboard_app.ui.settings.getSecurePrefs
import com.example.dashboard_app.data.model.StockItem
import com.example.dashboard_app.data.repository.StockRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class StocksViewModel(app: Application) : AndroidViewModel(app) {

    private val repo = StockRepository(AppDatabase.getInstance(app).stockDao())

    val stocks: StateFlow<List<StockItem>> = repo.stocks
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    private val _refreshMessage = MutableStateFlow<String?>(null)
    val refreshMessage: StateFlow<String?> = _refreshMessage.asStateFlow()

    fun save(id: Int, ticker: String, companyName: String, price: Double, shares: Double) {
        viewModelScope.launch {
            repo.save(StockItem(id = id, ticker = ticker.trim().uppercase(), companyName = companyName.trim(), price = price, shares = shares))
        }
    }

    fun delete(stock: StockItem) {
        viewModelScope.launch { repo.delete(stock) }
    }

    fun refreshAllPrices() {
        viewModelScope.launch {
            _isRefreshing.value = true
            _refreshMessage.value = null
            val currentStocks = repo.stocks.first()
            if (currentStocks.isEmpty()) {
                _isRefreshing.value = false
                return@launch
            }
            var successCount = 0
            val apiKey = runCatching {
                getSecurePrefs(getApplication()).getString(PREF_ALPHA_VANTAGE_KEY, "") ?: ""
            }.getOrDefault("").ifBlank { BuildConfig.ALPHA_VANTAGE_KEY }

            currentStocks.forEach { stock ->
                val ok = repo.refreshPrice(stock, apiKey)
                if (ok) successCount++
            }
            _refreshMessage.value = when {
                successCount == currentStocks.size -> "Prices updated"
                successCount == 0 -> "Update failed — check connection or API limit (25/day)"
                else -> "Updated $successCount of ${currentStocks.size} — API limit may be reached"
            }
            _isRefreshing.value = false
        }
    }

    fun clearMessage() { _refreshMessage.value = null }
}
