package com.example.dashboard_app.ui.home

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.dashboard_app.ui.budget.BudgetViewModel
import com.example.dashboard_app.ui.calendar.CalendarViewModel
import com.example.dashboard_app.ui.calendar.asReadableDateTime
import com.example.dashboard_app.ui.shifts.ShiftsViewModel
import com.example.dashboard_app.ui.stocks.StocksViewModel
import java.text.NumberFormat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private val moneyFmt: NumberFormat = NumberFormat.getCurrencyInstance(Locale.US)
private val timeFmt = SimpleDateFormat("h:mm a", Locale.US)
private val dateFmt = SimpleDateFormat("EEE, MMM d", Locale.US)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    navController: NavHostController,
    calendarViewModel: CalendarViewModel = viewModel(),
    budgetViewModel: BudgetViewModel = viewModel(),
    stocksViewModel: StocksViewModel = viewModel(),
    shiftsViewModel: ShiftsViewModel = viewModel()
) {
    val events by calendarViewModel.events.collectAsStateWithLifecycle()
    val transactions by budgetViewModel.transactions.collectAsStateWithLifecycle()
    val creditCards by budgetViewModel.creditCards.collectAsStateWithLifecycle()
    val stocks by stocksViewModel.stocks.collectAsStateWithLifecycle()
    val shifts by shiftsViewModel.shifts.collectAsStateWithLifecycle()

    val now = remember { System.currentTimeMillis() }
    val upcomingEvents = events.filter { it.dateTime >= now }.take(3)
    val upcomingShifts = shifts.filter { it.startTime >= now }.sortedBy { it.startTime }.take(3)
    val totalSpending = transactions.sumOf { it.amount }
    val totalCcBalance = creditCards.sumOf { it.balance }
    val portfolioValue = stocks.sumOf { it.price * it.shares }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Dashboard") },
                actions = {
                    IconButton(onClick = { navController.navigate("settings") }) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Upcoming events
            SummaryCard(title = "Upcoming events") {
                if (upcomingEvents.isEmpty()) {
                    Text("Nothing scheduled.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                } else {
                    upcomingEvents.forEach { e ->
                        Column(Modifier.padding(vertical = 4.dp)) {
                            Text(e.title, style = MaterialTheme.typography.titleSmall)
                            Text(
                                e.dateTime.asReadableDateTime(),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                    }
                }
            }

            // Upcoming shifts
            SummaryCard(title = "Upcoming shifts") {
                if (upcomingShifts.isEmpty()) {
                    Text("No upcoming shifts.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                } else {
                    upcomingShifts.forEach { s ->
                        Column(Modifier.padding(vertical = 4.dp)) {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("${s.employer} — ${s.title}", style = MaterialTheme.typography.titleSmall)
                            }
                            Text(
                                "${dateFmt.format(Date(s.startTime))}  ${timeFmt.format(Date(s.startTime))} – ${timeFmt.format(Date(s.endTime))}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                    }
                }
            }

            // Budget
            SummaryCard(title = "Monthly spending") {
                if (transactions.isEmpty() && creditCards.isEmpty()) {
                    Text("No budget data yet.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                } else {
                    if (transactions.isNotEmpty()) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Expenses", style = MaterialTheme.typography.bodyMedium)
                            Text(moneyFmt.format(totalSpending), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
                        }
                    }
                    if (creditCards.isNotEmpty()) {
                        Spacer(Modifier.height(4.dp))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("CC balances", style = MaterialTheme.typography.bodyMedium)
                            Text(moneyFmt.format(totalCcBalance), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
                        }
                        creditCards.forEach { card ->
                            Spacer(Modifier.height(2.dp))
                            Row(Modifier.fillMaxWidth().padding(start = 12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(card.name, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text(moneyFmt.format(card.balance), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }

            // Stocks
            SummaryCard(title = "Watchlist") {
                if (stocks.isEmpty()) {
                    Text("No stocks yet.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                } else {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Portfolio value", style = MaterialTheme.typography.bodyMedium)
                        Text(moneyFmt.format(portfolioValue), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
                    }
                    Spacer(Modifier.height(4.dp))
                    stocks.forEach { s ->
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(s.ticker, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(moneyFmt.format(s.price), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SummaryCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    ElevatedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(8.dp))
            content()
        }
    }
}
