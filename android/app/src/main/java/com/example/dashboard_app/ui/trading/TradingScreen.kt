package com.example.dashboard_app.ui.trading

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material.icons.filled.TrendingDown
import androidx.navigation.NavHostController
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.dashboard_app.data.network.TradingTrade
import java.text.NumberFormat
import java.util.Locale

private val nexusBlue = Color(0xFF0AAAFF)
private val nexusPurple = Color(0xFF8B5CF6)
private val nexusBg = Color(0xFF080F1A)
private val nexusSurface = Color(0xFF111827)
private val moneyFmt = NumberFormat.getCurrencyInstance(Locale.US)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TradingScreen(vm: TradingViewModel = viewModel(), navController: NavHostController? = null) {
    val state by vm.state.collectAsStateWithLifecycle()
    val status = state.status
    val trades = state.trades
    val closed = trades.filter { it.pnl_pct != null }
    val wins = closed.count { (it.pnl_pct ?: 0.0) > 0 }
    val totalPnl = closed.sumOf { it.pnl_pct ?: 0.0 }
    val winRate = if (closed.isNotEmpty()) wins.toFloat() / closed.size * 100 else 0f

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Nexus Trading", fontWeight = FontWeight.Bold)
                        Surface(color = nexusBlue.copy(alpha = 0.15f), shape = MaterialTheme.shapes.extraSmall) {
                            Text("PAPER", fontSize = 10.sp, color = nexusBlue, modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp), fontWeight = FontWeight.Bold)
                        }
                    }
                },
                actions = {
                    if (navController != null) {
                        IconButton(onClick = { navController.navigate("hermes_control") }) {
                            Icon(Icons.Default.Settings, "Hermes Control", tint = nexusBlue)
                        }
                    }
                    IconButton(onClick = { vm.refresh() }) {
                        Icon(Icons.Default.Refresh, "Refresh", tint = nexusBlue)
                    }
                }
            )
        }
    ) { padding ->
        if (state.isLoading && status == null) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = nexusBlue)
            }
            return@Scaffold
        }

        LazyColumn(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = PaddingValues(vertical = 12.dp)
        ) {
            // Error
            state.error?.let { err ->
                item {
                    ElevatedCard(Modifier.fillMaxWidth()) {
                        Text("Could not reach trading bot: $err", Modifier.padding(16.dp), color = MaterialTheme.colorScheme.error, fontSize = 13.sp)
                    }
                }
            }

            // Open trade banner
            status?.open_trade?.let { ot ->
                item {
                    Card(
                        Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF0D2137))
                    ) {
                        Column(Modifier.padding(16.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                Surface(color = Color(0xFF22C55E).copy(alpha = 0.2f), shape = MaterialTheme.shapes.extraSmall) {
                                    Text("⚡ LIVE TRADE", fontSize = 10.sp, color = Color(0xFF22C55E), modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp), fontWeight = FontWeight.Bold)
                                }
                            }
                            Spacer(Modifier.height(8.dp))
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("BTC/USDT ${(ot["direction"] as? String)?.uppercase() ?: ""}", fontWeight = FontWeight.Bold)
                                Text("Entry: ${moneyFmt.format((ot["entry_price"] as? Double) ?: 0.0)}", color = nexusBlue, fontWeight = FontWeight.SemiBold)
                            }
                            Text("v${ot["strategy_version"] as? String ?: "?"} · ${ot["source"] as? String ?: ""}", fontSize = 12.sp, color = Color(0xFF64748B))
                        }
                    }
                }
            }

            // Stats row
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    StatCard(Modifier.weight(1f), "BTC Price", status?.last_price?.let { moneyFmt.format(it) } ?: "—", nexusBlue)
                    StatCard(Modifier.weight(1f), "Total PnL", if (closed.isNotEmpty()) "${if (totalPnl >= 0) "+" else ""}${String.format("%.2f", totalPnl * 100)}%" else "—",
                        if (totalPnl >= 0) Color(0xFF22C55E) else Color(0xFFEF4444))
                }
            }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    StatCard(Modifier.weight(1f), "Win Rate", if (closed.isNotEmpty()) "${winRate.toInt()}%" else "—", Color(0xFF22C55E))
                    StatCard(Modifier.weight(1f), "Trades", "${closed.size}W/${closed.size - wins}L", MaterialTheme.colorScheme.onSurface)
                }
            }

            // Strategy
            status?.strategy?.let { strat ->
                item {
                    ElevatedCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp)) {
                            Text("Current Strategy", style = MaterialTheme.typography.labelMedium, color = Color(0xFF64748B))
                            Spacer(Modifier.height(8.dp))
                            Text(strat, fontSize = 12.sp, color = Color(0xFF94A3B8), fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
                        }
                    }
                }
            }

            // Trade history header
            if (closed.isNotEmpty()) {
                item {
                    Text("Recent Trades", style = MaterialTheme.typography.titleSmall, color = Color(0xFF64748B), modifier = Modifier.padding(top = 4.dp))
                }
                items(closed.reversed().take(25), key = { it.entry_ts ?: Math.random().toString() }) { trade ->
                    TradeRow(trade)
                }
            } else if (status != null) {
                item {
                    ElevatedCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                            Text("No trades yet", fontWeight = FontWeight.SemiBold)
                            Spacer(Modifier.height(4.dp))
                            Text("Waiting for 15m RSI < 35 entry · take-profit RSI > 55 · stop loss 1%", fontSize = 13.sp, color = Color(0xFF64748B))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StatCard(modifier: Modifier, label: String, value: String, valueColor: Color) {
    ElevatedCard(modifier) {
        Column(Modifier.padding(14.dp)) {
            Text(label, fontSize = 11.sp, color = Color(0xFF64748B), fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(4.dp))
            Text(value, fontSize = 18.sp, fontWeight = FontWeight.Bold, color = valueColor)
        }
    }
}

@Composable
private fun TradeRow(trade: TradingTrade) {
    val pnl = trade.pnl_pct ?: 0.0
    val isWin = pnl > 0
    val pnlColor = if (isWin) Color(0xFF22C55E) else Color(0xFFEF4444)
    val pnlStr = "${if (isWin) "+" else ""}${String.format("%.3f", pnl * 100)}%"

    ElevatedCard(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(
                if (isWin) Icons.Default.TrendingUp else Icons.Default.TrendingDown,
                null, tint = pnlColor, modifier = Modifier.size(20.dp)
            )
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(trade.direction?.uppercase() ?: "", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    Text("v${trade.strategy_version ?: "?"}", fontSize = 11.sp, color = Color(0xFF64748B))
                    trade.source?.let { src ->
                        Surface(color = if (src == "tradingview") nexusBlue.copy(0.15f) else Color(0xFF22C55E).copy(0.15f), shape = MaterialTheme.shapes.extraSmall) {
                            Text(src, fontSize = 10.sp, color = if (src == "tradingview") nexusBlue else Color(0xFF22C55E), modifier = Modifier.padding(horizontal = 5.dp, vertical = 1.dp))
                        }
                    }
                }
                Text(trade.entry_ts?.take(16)?.replace("T", " ") ?: "", fontSize = 11.sp, color = Color(0xFF475569))
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(pnlStr, color = pnlColor, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                Text(trade.exit_reason ?: "", fontSize = 10.sp, color = Color(0xFF475569))
            }
        }
    }
}
