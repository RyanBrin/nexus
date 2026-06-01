package com.example.dashboard_app.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.dashboard_app.ui.budget.BudgetViewModel
import com.example.dashboard_app.ui.calendar.CalendarViewModel
import com.example.dashboard_app.ui.calendar.asReadableDateTime
import com.example.dashboard_app.ui.shifts.ShiftsViewModel
import com.example.dashboard_app.ui.stocks.StocksViewModel
import com.example.dashboard_app.ui.theme.*
import java.text.NumberFormat
import java.text.SimpleDateFormat
import java.util.*

private val moneyFmt = NumberFormat.getCurrencyInstance(Locale.US)
private val timeFmt  = SimpleDateFormat("h:mm a", Locale.US)
private val dateFmt  = SimpleDateFormat("EEE, MMM d", Locale.US)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    navController: NavHostController,
    calendarViewModel: CalendarViewModel = viewModel(),
    budgetViewModel: BudgetViewModel = viewModel(),
    stocksViewModel: StocksViewModel = viewModel(),
    shiftsViewModel: ShiftsViewModel = viewModel()
) {
    val events    by calendarViewModel.events.collectAsStateWithLifecycle()
    val txns      by budgetViewModel.transactions.collectAsStateWithLifecycle()
    val cards     by budgetViewModel.creditCards.collectAsStateWithLifecycle()
    val stocks    by stocksViewModel.stocks.collectAsStateWithLifecycle()
    val shifts    by shiftsViewModel.shifts.collectAsStateWithLifecycle()

    val now              = remember { System.currentTimeMillis() }
    val upcomingEvents   = events.filter { it.dateTime >= now }.take(3)
    val upcomingShifts   = shifts.filter { it.startTime >= now }.sortedBy { it.startTime }.take(2)
    val totalSpending    = txns.sumOf { it.amount }
    val totalCcBalance   = cards.sumOf { it.balance }
    val portfolioValue   = stocks.sumOf { it.price * it.shares }

    Scaffold(
        containerColor = NexusBg,
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Nexus", fontWeight = FontWeight.ExtraBold, fontSize = 22.sp, color = NexusOnBg)
                        Text("Personal Command Center", fontSize = 11.sp, color = NexusSubtle)
                    }
                },
                actions = {
                    IconButton(onClick = { navController.navigate("settings") }) {
                        Icon(Icons.Default.Settings, "Settings", tint = NexusMuted)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = NexusBg)
            )
        }
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {

            // ── Quick stats row ───────────────────────────────────────────────
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                QuickStat(Modifier.weight(1f), "Portfolio", moneyFmt.format(portfolioValue), NexusBlue, Icons.Default.ShowChart)
                QuickStat(Modifier.weight(1f), "Spending", moneyFmt.format(totalSpending), NexusAmber, Icons.Default.Paid)
                QuickStat(Modifier.weight(1f), "CC Debt", moneyFmt.format(totalCcBalance), if (totalCcBalance > 500) NexusRed else NexusMuted, Icons.Default.CreditCard)
            }

            // ── Upcoming events ───────────────────────────────────────────────
            DashCard(
                title = "Upcoming Events",
                icon = Icons.Default.CalendarMonth,
                onTap = { navController.navigate("calendar") }
            ) {
                if (upcomingEvents.isEmpty()) {
                    EmptyState("Nothing scheduled")
                } else {
                    upcomingEvents.forEach { e ->
                        EventRow(title = e.title, subtitle = e.dateTime.asReadableDateTime())
                    }
                }
            }

            // ── Upcoming shifts ───────────────────────────────────────────────
            DashCard(
                title = "Upcoming Shifts",
                icon = Icons.Default.Work,
                onTap = { navController.navigate("calendar") }
            ) {
                if (upcomingShifts.isEmpty()) {
                    EmptyState("No upcoming shifts")
                } else {
                    upcomingShifts.forEach { s ->
                        val employerColor = if (s.employer == "Pebble Creek") NexusGreen else NexusBlue
                        EventRow(
                            title = "${s.employer} — ${s.title}",
                            subtitle = "${dateFmt.format(Date(s.startTime))}  ${timeFmt.format(Date(s.startTime))} – ${timeFmt.format(Date(s.endTime))}",
                            accentColor = employerColor
                        )
                    }
                }
            }

            // ── Budget ────────────────────────────────────────────────────────
            DashCard(
                title = "Budget",
                icon = Icons.Default.Paid,
                onTap = { navController.navigate("budget") }
            ) {
                if (txns.isEmpty() && cards.isEmpty()) {
                    EmptyState("No budget data yet")
                } else {
                    if (txns.isNotEmpty()) {
                        BudgetRow("Expenses this month", moneyFmt.format(totalSpending), NexusAmber)
                    }
                    if (cards.isNotEmpty()) {
                        BudgetRow("Credit card balances", moneyFmt.format(totalCcBalance),
                            if (totalCcBalance > 1000) NexusRed else NexusMuted)
                        cards.forEach { card ->
                            val util = if (card.limit > 0) card.balance / card.limit else 0.0
                            BudgetRow(
                                "  ${card.name}",
                                moneyFmt.format(card.balance),
                                if (util > 0.8) NexusRed else NexusMuted,
                                small = true
                            )
                        }
                    }
                }
            }

            // ── Stocks ────────────────────────────────────────────────────────
            DashCard(
                title = "Watchlist",
                icon = Icons.Default.ShowChart,
                onTap = { navController.navigate("stocks") }
            ) {
                if (stocks.isEmpty()) {
                    EmptyState("No stocks in watchlist")
                } else {
                    BudgetRow("Portfolio value", moneyFmt.format(portfolioValue), NexusBlue)
                    Spacer(Modifier.height(4.dp))
                    stocks.take(4).forEach { s ->
                        val changeColor = if (s.changePercent.startsWith("-")) NexusRed else NexusGreen
                        Row(
                            Modifier.fillMaxWidth().padding(vertical = 2.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(s.ticker, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = NexusOnSurface)
                            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                if (s.changePercent.isNotBlank()) {
                                    Text(s.changePercent, fontSize = 12.sp, color = changeColor, fontWeight = FontWeight.SemiBold)
                                }
                                Text(moneyFmt.format(s.price), fontSize = 13.sp, color = NexusMuted)
                            }
                        }
                    }
                    if (stocks.size > 4) {
                        Text("+${stocks.size - 4} more", fontSize = 11.sp, color = NexusSubtle, modifier = Modifier.padding(top = 2.dp))
                    }
                }
            }

            Spacer(Modifier.height(8.dp))
        }
    }
}

// ── Reusable components ───────────────────────────────────────────────────────

@Composable
private fun QuickStat(modifier: Modifier, label: String, value: String, color: Color, icon: ImageVector) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = NexusSurface),
        shape = MaterialTheme.shapes.medium
    ) {
        Column(Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Box(
                    Modifier.size(28.dp).clip(CircleShape).background(color.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(icon, null, tint = color, modifier = Modifier.size(15.dp))
                }
                Text(label, fontSize = 10.sp, color = NexusSubtle, fontWeight = FontWeight.SemiBold)
            }
            Spacer(Modifier.height(6.dp))
            Text(value, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = color, maxLines = 1)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DashCard(
    title: String,
    icon: ImageVector,
    onTap: () -> Unit,
    content: @Composable ColumnScope.() -> Unit
) {
    Card(
        onClick = onTap,
        colors = CardDefaults.cardColors(containerColor = NexusSurface),
        shape = MaterialTheme.shapes.large
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(icon, null, tint = NexusBlue, modifier = Modifier.size(16.dp))
                    Text(title, fontSize = 12.sp, fontWeight = FontWeight.Bold,
                        color = NexusMuted, letterSpacing = 0.5.sp)
                }
                Icon(Icons.Default.ChevronRight, null, tint = NexusDisabled, modifier = Modifier.size(16.dp))
            }
            Spacer(Modifier.height(10.dp))
            HorizontalDivider(color = NexusSurface2, thickness = 0.5.dp)
            Spacer(Modifier.height(10.dp))
            content()
        }
    }
}

@Composable
private fun EventRow(title: String, subtitle: String, accentColor: Color = NexusBlue) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            Modifier.width(3.dp).height(32.dp).clip(MaterialTheme.shapes.small)
                .background(accentColor)
        )
        Spacer(Modifier.width(10.dp))
        Column {
            Text(title, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = NexusOnBg, maxLines = 1)
            Text(subtitle, fontSize = 11.sp, color = NexusMuted)
        }
    }
}

@Composable
private fun BudgetRow(label: String, value: String, valueColor: Color, small: Boolean = false) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = if (small) 1.dp else 3.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, fontSize = if (small) 12.sp else 13.sp, color = if (small) NexusMuted else NexusOnSurface)
        Text(value, fontSize = if (small) 12.sp else 13.sp, fontWeight = FontWeight.Bold, color = valueColor)
    }
}

@Composable
private fun EmptyState(text: String) {
    Text(text, fontSize = 13.sp, color = NexusSubtle, modifier = Modifier.padding(vertical = 4.dp))
}
