package com.example.dashboard_app.ui.budget

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.dashboard_app.data.network.ExchangeTokenBody
import com.example.dashboard_app.data.network.PlaidAccount
import com.example.dashboard_app.data.network.PlaidService
import com.example.dashboard_app.data.network.PlaidTransaction
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PlaidState(
    val accounts: List<PlaidAccount> = emptyList(),
    val transactions: List<PlaidTransaction> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val connected: Boolean = false
)

class PlaidViewModel(app: Application) : AndroidViewModel(app) {
    private val service = PlaidService.instance

    private val _state = MutableStateFlow(PlaidState())
    val state = _state.asStateFlow()

    // One-shot event — emits the link token exactly once, not tied to recomposition
    private val _openLink = MutableSharedFlow<String>(extraBufferCapacity = 1)
    val openLink = _openLink.asSharedFlow()

    fun fetchLinkToken() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val resp = service.createLinkToken()
                _state.value = _state.value.copy(isLoading = false)
                _openLink.emit(resp.link_token)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = "Could not connect: ${e.message}")
            }
        }
    }

    fun exchangePublicToken(publicToken: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                service.exchangeToken(ExchangeTokenBody(publicToken))
                _state.value = _state.value.copy(isLoading = false, connected = true)
                loadAccounts()
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = "Token exchange failed: ${e.message}")
            }
        }
    }

    fun loadAccounts() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val acctResp = service.getAccounts()
                val txnResp = service.getTransactions(30)
                _state.value = _state.value.copy(
                    accounts = acctResp.accounts,
                    transactions = txnResp.transactions,
                    isLoading = false,
                    connected = acctResp.accounts.isNotEmpty()
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = "Could not load accounts: ${e.message}")
            }
        }
    }

    fun clearError() { _state.value = _state.value.copy(error = null) }
}
