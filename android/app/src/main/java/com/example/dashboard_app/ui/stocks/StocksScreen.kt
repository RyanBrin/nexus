package com.example.dashboard_app.ui.stocks

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.dashboard_app.data.model.StockItem
import java.text.NumberFormat
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

private val moneyFmt: NumberFormat = NumberFormat.getCurrencyInstance(Locale.US)
private val timeFmt: DateTimeFormatter =
    DateTimeFormatter.ofPattern("h:mm a", Locale.getDefault())

private fun Long.asTime(): String =
    if (this == 0L) "Never" else
        Instant.ofEpochMilli(this).atZone(ZoneId.systemDefault()).format(timeFmt)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StocksScreen(viewModel: StocksViewModel = viewModel()) {
    val stocks by viewModel.stocks.collectAsStateWithLifecycle()
    val isRefreshing by viewModel.isRefreshing.collectAsStateWithLifecycle()
    val refreshMessage by viewModel.refreshMessage.collectAsStateWithLifecycle()
    var editing by remember { mutableStateOf<StockItem?>(null) }

    val totalValue = stocks.sumOf { it.price * it.shares }
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(refreshMessage) {
        refreshMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearMessage()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Stocks") },
                actions = {
                    if (isRefreshing) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp).padding(end = 4.dp),
                            strokeWidth = 2.dp
                        )
                    } else {
                        IconButton(onClick = { viewModel.refreshAllPrices() }) {
                            Icon(Icons.Default.Refresh, contentDescription = "Refresh prices")
                        }
                    }
                }
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = {
                editing = StockItem(ticker = "", price = 0.0, shares = 0.0)
            }) { Icon(Icons.Default.Add, contentDescription = "Add stock") }
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            if (stocks.isNotEmpty()) {
                Surface(tonalElevation = 2.dp) {
                    Row(
                        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Portfolio value", style = MaterialTheme.typography.titleSmall)
                        Text(
                            moneyFmt.format(totalValue),
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }
            if (stocks.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        "No stocks yet.\nTap + to add a ticker.",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    items(stocks, key = { it.id }) { stock ->
                        StockCard(
                            stock = stock,
                            onClick = { editing = stock },
                            onDelete = { viewModel.delete(stock) }
                        )
                    }
                }
            }
        }
    }

    editing?.let { s ->
        StockDialog(
            initial = s,
            onDismiss = { editing = null },
            onSave = { ticker, company, price, shares ->
                viewModel.save(s.id, ticker, company, price, shares)
                editing = null
            }
        )
    }
}

@Composable
private fun StockCard(stock: StockItem, onClick: () -> Unit, onDelete: () -> Unit) {
    val changePct = stock.changePercent.toDoubleOrNull()
    val changeColor = when {
        changePct == null || changePct == 0.0 -> Color.Unspecified
        changePct > 0 -> Color(0xFF2E7D32)
        else -> MaterialTheme.colorScheme.error
    }
    val changeLabel = when {
        changePct == null || stock.lastUpdated == 0L -> ""
        changePct >= 0 -> "+${stock.changePercent}%"
        else -> "${stock.changePercent}%"
    }

    Card(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(stock.ticker, style = MaterialTheme.typography.titleMedium)
                    if (changeLabel.isNotEmpty()) {
                        Text(changeLabel, style = MaterialTheme.typography.labelMedium, color = changeColor)
                    }
                }
                if (stock.companyName.isNotBlank()) {
                    Text(stock.companyName, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Spacer(Modifier.height(4.dp))
                Text(
                    "${stock.shares} shares @ ${moneyFmt.format(stock.price)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                if (stock.lastUpdated > 0L) {
                    Text(
                        "Updated ${stock.lastUpdated.asTime()}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    moneyFmt.format(stock.price * stock.shares),
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.primary
                )
                Text("value", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            IconButton(onClick = onDelete) {
                Icon(Icons.Default.DeleteOutline, contentDescription = "Delete")
            }
        }
    }
}

@Composable
private fun StockDialog(
    initial: StockItem,
    onDismiss: () -> Unit,
    onSave: (ticker: String, companyName: String, price: Double, shares: Double) -> Unit
) {
    var ticker by remember { mutableStateOf(initial.ticker) }
    var companyName by remember { mutableStateOf(initial.companyName) }
    var priceText by remember { mutableStateOf(if (initial.price == 0.0) "" else initial.price.toString()) }
    var sharesText by remember { mutableStateOf(if (initial.shares == 0.0) "" else initial.shares.toString()) }
    val isNew = initial.id == 0
    val tickerValid = ticker.isNotBlank()
    val priceValid = priceText.toDoubleOrNull()?.let { it >= 0 } == true
    val sharesValid = sharesText.toDoubleOrNull()?.let { it >= 0 } == true

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (isNew) "Add stock" else "Edit stock") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = ticker,
                    onValueChange = { ticker = it.uppercase() },
                    label = { Text("Ticker symbol") },
                    singleLine = true,
                    isError = !tickerValid,
                    supportingText = { if (!tickerValid) Text("Required") },
                    keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Characters),
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = companyName,
                    onValueChange = { companyName = it },
                    label = { Text("Company name (optional)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = priceText,
                    onValueChange = { priceText = it },
                    label = { Text("Price per share ($) — live refresh will update this") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = sharesText,
                    onValueChange = { sharesText = it },
                    label = { Text("Shares owned") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            TextButton(
                enabled = tickerValid && priceValid && sharesValid,
                onClick = { onSave(ticker, companyName, priceText.toDouble(), sharesText.toDouble()) }
            ) { Text("Save") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}
