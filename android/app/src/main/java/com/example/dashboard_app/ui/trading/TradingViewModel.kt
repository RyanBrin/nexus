package com.example.dashboard_app.ui.trading

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.dashboard_app.data.network.TradingService
import com.example.dashboard_app.data.network.TradingStatus
import com.example.dashboard_app.data.network.TradingTrade
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class TradingUiState(
    val status: TradingStatus? = null,
    val trades: List<TradingTrade> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

class TradingViewModel(app: Application) : AndroidViewModel(app) {
    private val service = TradingService.instance
    private val _state = MutableStateFlow(TradingUiState())
    val state = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val status = service.getStatus()
                val trades = service.getTrades()
                _state.value = TradingUiState(status = status, trades = trades, isLoading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }
}
