package com.example.dashboard_app.ui.trading

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
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
import com.example.dashboard_app.data.network.HermesTradeIdea

private val nexusBlue   = Color(0xFF0AAAFF)
private val nexusPurple = Color(0xFF8B5CF6)
private val green       = Color(0xFF22C55E)
private val red         = Color(0xFFEF4444)
private val amber       = Color(0xFFF59E0B)
private val surface     = Color(0xFF111827)
private val border      = Color(0xFF1E293B)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HermesControlScreen(vm: HermesControlViewModel = viewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabs = listOf("Status", "Trade Ideas", "Risk Rules")

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Hermes Control", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = { vm.refresh() }) {
                        Icon(Icons.Default.Refresh, "Refresh", tint = nexusBlue)
                    }
                }
            )
        }
    ) { padding ->
        if (state.isLoading && state.recentIdeas.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = nexusBlue)
            }
            return@Scaffold
        }

        Column(Modifier.fillMaxSize().padding(padding)) {
            PrimaryTabRow(selectedTabIndex = selectedTab) {
                tabs.forEachIndexed { i, t -> Tab(selected = selectedTab == i, onClick = { selectedTab = i }, text = { Text(t) }) }
            }
            when (selectedTab) {
                0 -> StatusTab(state)
                1 -> IdeasTab(state.recentIdeas)
                2 -> RiskRulesTab(state.riskRules)
            }
        }
    }
}

@Composable
private fun StatusTab(state: HermesControlState) {
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            // Running status
            ElevatedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text("Hermes Status", style = MaterialTheme.typography.titleSmall)
                        Surface(
                            color = if (state.isRunning) green.copy(0.15f) else red.copy(0.15f),
                            shape = MaterialTheme.shapes.extraSmall
                        ) {
                            Text(
                                if (state.isRunning) "● Running" else "○ Stopped",
                                color = if (state.isRunning) green else red,
                                fontSize = 11.sp, fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                            )
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                    StatusRow("Mode", state.mode.replace("_", " ").uppercase())
                    StatusRow("BTC Loop", if (state.btcLoopRunning) "Running" else "Stopped", if (state.btcLoopRunning) green else red)
                    StatusRow("Stock Loop", if (state.stockLoopRunning) "Running" else "Stopped", if (state.stockLoopRunning) green else red)
                    StatusRow("Active Strategy", state.activeStrategy)
                    StatusRow("Last BTC Tick", state.lastBtcTick?.take(16)?.replace("T", " ") ?: "—")
                    StatusRow("Last Stock Scan", state.lastStockScan?.take(16)?.replace("T", " ") ?: "—")
                }
            }
        }

        item {
            // Ideas summary
            ElevatedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("Trade Ideas Summary", style = MaterialTheme.typography.titleSmall)
                    Spacer(Modifier.height(10.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceAround) {
                        StatChip("Total", state.totalIdeas.toString(), nexusBlue)
                        StatChip("Approved", state.approved.toString(), green)
                        StatChip("Rejected", state.rejected.toString(), red)
                        StatChip("Rate", "${state.approvalRatePct}%", amber)
                    }
                }
            }
        }

        if (state.errors.isNotEmpty()) {
            item {
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp)) {
                        Text("Recent Errors", style = MaterialTheme.typography.titleSmall, color = red)
                        Spacer(Modifier.height(6.dp))
                        state.errors.forEach { e ->
                            Text(e["error"] as? String ?: "unknown", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }

        item {
            Text("Paper trading — no real money at risk", fontSize = 11.sp, color = Color(0xFF475569), modifier = Modifier.padding(top = 4.dp))
        }
    }
}

@Composable
private fun StatusRow(label: String, value: String, valueColor: Color = MaterialTheme.colorScheme.onSurface) {
    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, fontSize = 13.sp, color = Color(0xFF64748B))
        Text(value, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = valueColor)
    }
}

@Composable
private fun StatChip(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, fontSize = 20.sp, fontWeight = FontWeight.Bold, color = color)
        Text(label, fontSize = 10.sp, color = Color(0xFF64748B))
    }
}

@Composable
private fun IdeasTab(ideas: List<HermesTradeIdea>) {
    if (ideas.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text("No trade ideas yet", fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(4.dp))
                Text("Hermes will log every setup it considers here", fontSize = 13.sp, color = Color(0xFF64748B))
            }
        }
        return
    }

    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(ideas.reversed(), key = { it.created_at + it.ticker }) { idea ->
            IdeaCard(idea)
        }
    }
}

@Composable
private fun IdeaCard(idea: HermesTradeIdea) {
    val statusColor = when (idea.status) {
        "approved" -> green
        "rejected" -> red
        else -> amber
    }
    val statusIcon = when (idea.status) { "approved" -> "✓" ; "rejected" -> "✗" ; else -> "◌" }

    ElevatedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text(idea.ticker, fontWeight = FontWeight.ExtraBold, fontSize = 15.sp)
                Spacer(Modifier.width(8.dp))
                Surface(color = statusColor.copy(0.15f), shape = MaterialTheme.shapes.extraSmall) {
                    Text("$statusIcon ${idea.status.uppercase()}", color = statusColor, fontSize = 10.sp,
                        fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp))
                }
                Spacer(Modifier.weight(1f))
                Text(idea.created_at.take(16).replace("T", " "), fontSize = 11.sp, color = Color(0xFF475569))
            }
            Spacer(Modifier.height(8.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                InfoChip("Entry", idea.entry_price?.let { "$${"%.2f".format(it)}" } ?: "—")
                InfoChip("Stop", idea.stop_price?.let { "$${"%.2f".format(it)}" } ?: "—", red)
                InfoChip("Target", idea.target_price?.let { "$${"%.2f".format(it)}" } ?: "—", green)
                InfoChip("R/R", idea.risk_reward?.let { "${it}R" } ?: "—")
                InfoChip("Conf", "${idea.confidence}/100")
            }
            if (idea.rejection_reason.isNotBlank()) {
                Spacer(Modifier.height(4.dp))
                Text("Blocked: ${idea.rejection_reason.replace("_", " ")}", fontSize = 12.sp, color = red)
            }
            if (idea.chart_reason.isNotBlank()) {
                Spacer(Modifier.height(4.dp))
                Text(idea.chart_reason, fontSize = 12.sp, color = Color(0xFF94A3B8))
            }
            if (idea.hermes_notes.isNotBlank()) {
                Spacer(Modifier.height(4.dp))
                Text("🤖 ${idea.hermes_notes}", fontSize = 11.sp, color = Color(0xFF64748B))
            }
        }
    }
}

@Composable
private fun InfoChip(label: String, value: String, valueColor: Color = MaterialTheme.colorScheme.onSurface) {
    Column {
        Text(label, fontSize = 9.sp, color = Color(0xFF475569))
        Text(value, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = valueColor)
    }
}

@Composable
private fun RiskRulesTab(rules: Map<String, Any?>) {
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(vertical = 12.dp)
    ) {
        item {
            ElevatedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("🔒 Active Risk Rules", style = MaterialTheme.typography.titleSmall)
                    Spacer(Modifier.height(4.dp))
                    Text("These are hardcoded — the learning system cannot change them.",
                        fontSize = 12.sp, color = Color(0xFF64748B))
                    Spacer(Modifier.height(12.dp))
                    rules.filter { it.key != "note" }.forEach { (k, v) ->
                        val isSafe = v == false || (v is Number && v.toDouble() < 3.0 && k.contains("loss"))
                        Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(k.replace("_", " "), fontSize = 13.sp, color = Color(0xFF94A3B8))
                            Text(v.toString(), fontSize = 13.sp, fontWeight = FontWeight.Bold,
                                color = if (v == false) red else if (v == true) green else nexusBlue)
                        }
                        HorizontalDivider(color = Color(0xFF1E293B))
                    }
                    rules["note"]?.let {
                        Spacer(Modifier.height(8.dp))
                        Text(it.toString(), fontSize = 11.sp, color = Color(0xFF475569), fontStyle = androidx.compose.ui.text.font.FontStyle.Italic)
                    }
                }
            }
        }
    }
}
