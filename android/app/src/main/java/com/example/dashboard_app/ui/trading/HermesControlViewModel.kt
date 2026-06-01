package com.example.dashboard_app.ui.trading

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.dashboard_app.data.network.HermesService
import com.example.dashboard_app.data.network.HermesTradeIdea
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class HermesControlState(
    val isRunning: Boolean = false,
    val mode: String = "paper_trading",
    val btcLoopRunning: Boolean = false,
    val stockLoopRunning: Boolean = false,
    val lastBtcTick: String? = null,
    val lastStockScan: String? = null,
    val activeStrategy: String = "v01",
    val totalIdeas: Int = 0,
    val approved: Int = 0,
    val rejected: Int = 0,
    val approvalRatePct: Double = 0.0,
    val recentIdeas: List<HermesTradeIdea> = emptyList(),
    val riskRules: Map<String, Any?> = emptyMap(),
    val errors: List<Map<String, Any?>> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
)

class HermesControlViewModel(app: Application) : AndroidViewModel(app) {
    private val service = HermesService.instance
    private val _state = MutableStateFlow(HermesControlState())
    val state = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val status = service.getStatus()
                val ideas = service.getTradeIdeas(limit = 20)
                val stats = service.getIdeaStats()
                val rules = service.getRiskRules()

                val s = status.status
                @Suppress("UNCHECKED_CAST")
                val errs = (s["errors"] as? List<Map<String, Any?>>).orEmpty()

                _state.value = HermesControlState(
                    isRunning = s["running"] as? Boolean ?: false,
                    mode = s["mode"] as? String ?: "paper_trading",
                    btcLoopRunning = s["btc_loop_running"] as? Boolean ?: false,
                    stockLoopRunning = s["stock_loop_running"] as? Boolean ?: false,
                    lastBtcTick = s["last_btc_tick"] as? String,
                    lastStockScan = s["last_stock_scan"] as? String,
                    activeStrategy = s["active_strategy"] as? String ?: "v01",
                    totalIdeas = stats.total_ideas,
                    approved = stats.approved,
                    rejected = stats.rejected,
                    approvalRatePct = stats.approval_rate_pct,
                    recentIdeas = ideas,
                    riskRules = rules,
                    errors = errs.takeLast(5),
                    isLoading = false,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }
}
