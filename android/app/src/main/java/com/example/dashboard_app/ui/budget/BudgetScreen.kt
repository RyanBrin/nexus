package com.example.dashboard_app.ui.budget

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.dashboard_app.data.model.BudgetGoal
import com.example.dashboard_app.data.model.CreditCard
import com.example.dashboard_app.data.model.Transaction
import com.plaid.link.OpenPlaidLink
import com.plaid.link.configuration.LinkTokenConfiguration
import com.plaid.link.result.LinkExit
import com.plaid.link.result.LinkSuccess
import java.text.NumberFormat
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

private val nexusBlue = Color(0xFF0AAAFF)
private val nexusPurple = Color(0xFF8B5CF6)

private val moneyFmt: NumberFormat = NumberFormat.getCurrencyInstance(Locale.US)
private val shortDateFmt: DateTimeFormatter =
    DateTimeFormatter.ofPattern("MMM d", Locale.getDefault())

fun Long.asShortDate(): String =
    Instant.ofEpochMilli(this).atZone(ZoneId.systemDefault()).format(shortDateFmt)

val CATEGORIES = listOf("Food", "Transport", "Housing", "Entertainment", "Health", "Shopping", "Other")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BudgetScreen(
    viewModel: BudgetViewModel = viewModel(),
    plaidViewModel: PlaidViewModel = viewModel(),
    goalsViewModel: BudgetGoalViewModel = viewModel()
) {
    val transactions by viewModel.transactions.collectAsStateWithLifecycle()
    val creditCards by viewModel.creditCards.collectAsStateWithLifecycle()
    val plaidState by plaidViewModel.state.collectAsStateWithLifecycle()
    val goals by goalsViewModel.goals.collectAsStateWithLifecycle()
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabs = listOf("Expenses", "Goals", "Credit Cards", "Bank")

    // Seed default goals on first launch
    LaunchedEffect(Unit) { goalsViewModel.seedDefaults() }

    var editingTransaction by remember { mutableStateOf<Transaction?>(null) }
    var editingCard by remember { mutableStateOf<CreditCard?>(null) }

    // Plaid Link launcher
    val linkLauncher = rememberLauncherForActivityResult(OpenPlaidLink()) { result ->
        when (result) {
            is LinkSuccess -> plaidViewModel.exchangePublicToken(result.publicToken)
            is LinkExit -> plaidViewModel.clearError()
            else -> {}
        }
    }

    // Collect one-shot launch events from the ViewModel
    LaunchedEffect(Unit) {
        plaidViewModel.openLink.collect { token ->
            linkLauncher.launch(LinkTokenConfiguration.Builder().token(token).build())
        }
    }

    // Load accounts on first open of Bank tab
    LaunchedEffect(selectedTab) {
        if (selectedTab == 3 && plaidState.accounts.isEmpty() && !plaidState.isLoading) {
            plaidViewModel.loadAccounts()
        }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("Budget") }) },
        floatingActionButton = {
            if (selectedTab == 0) {
                FloatingActionButton(onClick = {
                    editingTransaction = Transaction(description = "", amount = 0.0, category = CATEGORIES[0])
                }) { Icon(Icons.Default.Add, contentDescription = "Add") }
            } else if (selectedTab == 2) {
                FloatingActionButton(onClick = {
                    editingCard = CreditCard(name = "", balance = 0.0, limit = 0.0)
                }) { Icon(Icons.Default.Add, contentDescription = "Add") }
            }
        }
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            PrimaryTabRow(selectedTabIndex = selectedTab) {
                tabs.forEachIndexed { i, title ->
                    Tab(selected = selectedTab == i, onClick = { selectedTab = i }, text = { Text(title) })
                }
            }

            when (selectedTab) {
                0 -> ExpensesTab(
                    transactions = transactions,
                    onEdit = { editingTransaction = it },
                    onDelete = { viewModel.deleteTransaction(it) }
                )
                1 -> GoalsTab(
                    goals = goals,
                    transactions = transactions,
                    onSave = { goalsViewModel.save(it) },
                    onDelete = { goalsViewModel.delete(it) }
                )
                2 -> CreditCardsTab(
                    cards = creditCards,
                    onEdit = { editingCard = it },
                    onDelete = { viewModel.deleteCreditCard(it) }
                )
                3 -> BankTab(
                    state = plaidState,
                    onConnectBank = { plaidViewModel.fetchLinkToken() },
                    onRefresh = { plaidViewModel.loadAccounts() }
                )
            }
        }
    }

    editingTransaction?.let { t ->
        TransactionDialog(
            initial = t,
            onDismiss = { editingTransaction = null },
            onSave = { desc, amount, category, date ->
                viewModel.saveTransaction(t.id, desc, amount, category, date)
                editingTransaction = null
            }
        )
    }

    editingCard?.let { c ->
        CreditCardDialog(
            initial = c,
            onDismiss = { editingCard = null },
            onSave = { name, balance, limit ->
                viewModel.saveCreditCard(c.id, name, balance, limit)
                editingCard = null
            }
        )
    }
}

@Composable
private fun ExpensesTab(
    transactions: List<Transaction>,
    onEdit: (Transaction) -> Unit,
    onDelete: (Transaction) -> Unit
) {
    val total = transactions.sumOf { it.amount }
    Column(Modifier.fillMaxSize()) {
        if (transactions.isNotEmpty()) {
            Surface(tonalElevation = 2.dp) {
                Row(
                    Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Total", style = MaterialTheme.typography.titleSmall)
                    Text(
                        moneyFmt.format(total),
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }
        if (transactions.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text(
                    "No expenses yet.\nTap + to add one.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        } else {
            LazyColumn(
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(transactions, key = { it.id }) { t ->
                    TransactionCard(t, onClick = { onEdit(t) }, onDelete = { onDelete(t) })
                }
            }
        }
    }
}

@Composable
private fun TransactionCard(t: Transaction, onClick: () -> Unit, onDelete: () -> Unit) {
    Card(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(t.description, style = MaterialTheme.typography.titleSmall)
                Spacer(Modifier.height(2.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    AssistChip(onClick = {}, label = { Text(t.category, style = MaterialTheme.typography.labelSmall) })
                    Text(
                        t.date.asShortDate(),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.align(Alignment.CenterVertically)
                    )
                }
            }
            Text(
                moneyFmt.format(t.amount),
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.primary
            )
            IconButton(onClick = onDelete) {
                Icon(Icons.Default.DeleteOutline, contentDescription = "Delete")
            }
        }
    }
}

@Composable
private fun CreditCardsTab(
    cards: List<CreditCard>,
    onEdit: (CreditCard) -> Unit,
    onDelete: (CreditCard) -> Unit
) {
    if (cards.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(
                "No credit cards yet.\nTap + to add one.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    } else {
        LazyColumn(
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            items(cards, key = { it.id }) { card ->
                CreditCardCard(card, onClick = { onEdit(card) }, onDelete = { onDelete(card) })
            }
        }
    }
}

@Composable
private fun CreditCardCard(card: CreditCard, onClick: () -> Unit, onDelete: () -> Unit) {
    Card(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(card.name, style = MaterialTheme.typography.titleSmall)
                Spacer(Modifier.height(4.dp))
                LinearProgressIndicator(
                    progress = { if (card.limit > 0) (card.balance / card.limit).toFloat().coerceIn(0f, 1f) else 0f },
                    modifier = Modifier.fillMaxWidth().padding(end = 8.dp),
                    color = if (card.limit > 0 && card.balance / card.limit > 0.8)
                        MaterialTheme.colorScheme.error
                    else
                        MaterialTheme.colorScheme.primary
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    "${moneyFmt.format(card.balance)} of ${moneyFmt.format(card.limit)} limit",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            IconButton(onClick = onDelete) {
                Icon(Icons.Default.DeleteOutline, contentDescription = "Delete")
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TransactionDialog(
    initial: Transaction,
    onDismiss: () -> Unit,
    onSave: (description: String, amount: Double, category: String, date: Long) -> Unit
) {
    var description by remember { mutableStateOf(initial.description) }
    var amountText by remember { mutableStateOf(if (initial.amount == 0.0) "" else initial.amount.toString()) }
    var category by remember { mutableStateOf(initial.category.ifBlank { CATEGORIES[0] }) }
    var categoryExpanded by remember { mutableStateOf(false) }
    val isNew = initial.id == 0
    val descValid = description.isNotBlank()
    val amountValid = amountText.toDoubleOrNull()?.let { it > 0 } == true

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (isNew) "New expense" else "Edit expense") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Description") },
                    singleLine = true,
                    isError = !descValid,
                    supportingText = { if (!descValid) Text("Required") },
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = amountText,
                    onValueChange = { amountText = it },
                    label = { Text("Amount ($)") },
                    singleLine = true,
                    isError = !amountValid && amountText.isNotEmpty(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.fillMaxWidth()
                )
                ExposedDropdownMenuBox(
                    expanded = categoryExpanded,
                    onExpandedChange = { categoryExpanded = it }
                ) {
                    OutlinedTextField(
                        value = category,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Category") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = categoryExpanded) },
                        modifier = Modifier.fillMaxWidth().menuAnchor(ExposedDropdownMenuAnchorType.PrimaryNotEditable)
                    )
                    ExposedDropdownMenu(
                        expanded = categoryExpanded,
                        onDismissRequest = { categoryExpanded = false }
                    ) {
                        CATEGORIES.forEach { cat ->
                            DropdownMenuItem(
                                text = { Text(cat) },
                                onClick = { category = cat; categoryExpanded = false }
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(
                enabled = descValid && amountValid,
                onClick = {
                    onSave(description, amountText.toDouble(), category, System.currentTimeMillis())
                }
            ) { Text("Save") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
private fun CreditCardDialog(
    initial: CreditCard,
    onDismiss: () -> Unit,
    onSave: (name: String, balance: Double, limit: Double) -> Unit
) {
    var name by remember { mutableStateOf(initial.name) }
    var balanceText by remember { mutableStateOf(if (initial.balance == 0.0) "" else initial.balance.toString()) }
    var limitText by remember { mutableStateOf(if (initial.limit == 0.0) "" else initial.limit.toString()) }
    val isNew = initial.id == 0
    val nameValid = name.isNotBlank()
    val balanceValid = balanceText.toDoubleOrNull() != null
    val limitValid = limitText.toDoubleOrNull()?.let { it >= 0 } == true

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (isNew) "New credit card" else "Edit credit card") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Card name") },
                    singleLine = true,
                    isError = !nameValid,
                    supportingText = { if (!nameValid) Text("Required") },
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = balanceText,
                    onValueChange = { balanceText = it },
                    label = { Text("Current balance ($)") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = limitText,
                    onValueChange = { limitText = it },
                    label = { Text("Credit limit ($)") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            TextButton(
                enabled = nameValid && balanceValid && limitValid,
                onClick = { onSave(name, balanceText.toDouble(), limitText.toDouble()) }
            ) { Text("Save") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

// ── Goals Tab ─────────────────────────────────────────────────────────────────

private val chartColors = listOf(
    Color(0xFF0AAAFF), Color(0xFF8B5CF6), Color(0xFF06B6D4), Color(0xFF22C55E),
    Color(0xFFF59E0B), Color(0xFFEF4444), Color(0xFFEC4899), Color(0xFF84CC16)
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun GoalsTab(
    goals: List<BudgetGoal>,
    transactions: List<Transaction>,
    onSave: (BudgetGoal) -> Unit,
    onDelete: (BudgetGoal) -> Unit
) {
    var editingGoal by remember { mutableStateOf<BudgetGoal?>(null) }

    // Map spending per category from transactions
    val spendingByCategory = transactions.groupBy { it.category }
        .mapValues { (_, txns) -> txns.sumOf { it.amount } }

    val totalCap = goals.sumOf { it.monthlyCapDollars }
    val totalSpent = spendingByCategory.values.sum()

    editingGoal?.let { goal ->
        GoalEditDialog(
            initial = goal,
            onDismiss = { editingGoal = null },
            onSave = { onSave(it); editingGoal = null }
        )
    }

    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        // Summary header
        item {
            ElevatedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text("Monthly Budget", style = MaterialTheme.typography.labelSmall, color = Color(0xFF64748B))
                            Text(moneyFmt.format(totalCap), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = nexusBlue)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("Spent This Month", style = MaterialTheme.typography.labelSmall, color = Color(0xFF64748B))
                            Text(moneyFmt.format(totalSpent), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold,
                                color = if (totalSpent > totalCap) Color(0xFFEF4444) else Color(0xFF22C55E))
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                    LinearProgressIndicator(
                        progress = { (totalSpent / totalCap).toFloat().coerceIn(0f, 1f) },
                        modifier = Modifier.fillMaxWidth(),
                        color = if (totalSpent > totalCap) Color(0xFFEF4444) else nexusBlue,
                        trackColor = Color(0xFF1E293B)
                    )
                    Spacer(Modifier.height(4.dp))
                    Text("${moneyFmt.format(totalCap - totalSpent)} remaining", fontSize = 12.sp, color = Color(0xFF64748B))
                }
            }
        }

        // Donut chart
        if (goals.isNotEmpty()) {
            item {
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text("Spending by Category", style = MaterialTheme.typography.titleSmall, color = Color(0xFF64748B))
                        Spacer(Modifier.height(12.dp))
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            // Donut chart
                            Box(Modifier.size(120.dp), contentAlignment = Alignment.Center) {
                                Canvas(Modifier.size(120.dp)) {
                                    val total = goals.sumOf { spendingByCategory[it.category] ?: 0.0 }.takeIf { it > 0 } ?: 1.0
                                    var startAngle = -90f
                                    goals.forEachIndexed { i, goal ->
                                        val spent = spendingByCategory[goal.category] ?: 0.0
                                        val sweep = (spent / total * 360f).toFloat()
                                        drawArc(
                                            color = chartColors[i % chartColors.size],
                                            startAngle = startAngle,
                                            sweepAngle = sweep,
                                            useCenter = false,
                                            style = Stroke(width = 24f),
                                            topLeft = Offset(12f, 12f),
                                            size = Size(size.width - 24f, size.height - 24f)
                                        )
                                        startAngle += sweep
                                    }
                                }
                            }
                            Spacer(Modifier.width(16.dp))
                            // Legend
                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                goals.take(5).forEachIndexed { i, goal ->
                                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                        Surface(modifier = Modifier.size(10.dp), color = chartColors[i % chartColors.size], shape = MaterialTheme.shapes.extraSmall) {}
                                        Text("${goal.emoji} ${goal.category}", fontSize = 11.sp, maxLines = 1)
                                    }
                                }
                                if (goals.size > 5) Text("+${goals.size - 5} more", fontSize = 10.sp, color = Color(0xFF64748B))
                            }
                        }
                    }
                }
            }
        }

        // Per-category goal rows
        items(goals, key = { it.category }) { goal ->
            val spent = spendingByCategory[goal.category] ?: 0.0
            val pct = (spent / goal.monthlyCapDollars).coerceIn(0.0, 1.0).toFloat()
            val overBudget = spent > goal.monthlyCapDollars

            ElevatedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text("${goal.emoji} ${goal.category}", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(
                                "${moneyFmt.format(spent)} / ${moneyFmt.format(goal.monthlyCapDollars)}",
                                fontSize = 13.sp,
                                color = if (overBudget) Color(0xFFEF4444) else Color(0xFF22C55E),
                                fontWeight = FontWeight.Bold
                            )
                            IconButton(onClick = { editingGoal = goal }, modifier = Modifier.size(28.dp)) {
                                Icon(Icons.Default.Edit, "Edit", tint = Color(0xFF64748B), modifier = Modifier.size(16.dp))
                            }
                        }
                    }
                    Spacer(Modifier.height(6.dp))
                    LinearProgressIndicator(
                        progress = { pct },
                        modifier = Modifier.fillMaxWidth(),
                        color = if (overBudget) Color(0xFFEF4444) else nexusBlue,
                        trackColor = Color(0xFF1E293B)
                    )
                    Spacer(Modifier.height(2.dp))
                    Text(
                        if (overBudget) "${moneyFmt.format(spent - goal.monthlyCapDollars)} over budget"
                        else "${moneyFmt.format(goal.monthlyCapDollars - spent)} remaining",
                        fontSize = 11.sp,
                        color = Color(0xFF64748B)
                    )
                }
            }
        }
    }
}

@Composable
private fun GoalEditDialog(
    initial: BudgetGoal,
    onDismiss: () -> Unit,
    onSave: (BudgetGoal) -> Unit
) {
    var capText by remember { mutableStateOf(initial.monthlyCapDollars.toString()) }
    val valid = capText.toDoubleOrNull()?.let { it >= 0 } == true

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("${initial.emoji} ${initial.category}") },
        text = {
            OutlinedTextField(
                value = capText,
                onValueChange = { capText = it },
                label = { Text("Monthly cap ($)") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
        },
        confirmButton = {
            TextButton(enabled = valid, onClick = {
                onSave(initial.copy(monthlyCapDollars = capText.toDouble()))
            }) { Text("Save") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
private fun BankTab(
    state: PlaidState,
    onConnectBank: () -> Unit,
    onRefresh: () -> Unit
) {
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("Connected Accounts", style = MaterialTheme.typography.titleMedium)
                Row {
                    if (state.accounts.isNotEmpty()) {
                        IconButton(onClick = onRefresh) { Icon(Icons.Default.Refresh, "Refresh") }
                    }
                    Button(onClick = onConnectBank, enabled = !state.isLoading) {
                        Text(if (state.connected) "Add Account" else "Connect Bank")
                    }
                }
            }
        }

        if (state.isLoading) {
            item { Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator() } }
        }

        state.error?.let { err ->
            item { ElevatedCard(Modifier.fillMaxWidth()) { Text(err, modifier = Modifier.padding(16.dp), color = MaterialTheme.colorScheme.error) } }
        }

        if (state.accounts.isEmpty() && !state.isLoading) {
            item {
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("No accounts connected", style = MaterialTheme.typography.titleSmall)
                        Text("Tap 'Connect Bank' to link your bank account and see live balances and transactions.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        } else {
            items(state.accounts) { acct ->
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(acct.name, style = MaterialTheme.typography.titleSmall)
                            Text("${acct.type.replaceFirstChar { it.uppercase() }} · ${acct.subtype}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text(moneyFmt.format(acct.current_balance ?: 0.0), style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
                            if (acct.available_balance != null && acct.available_balance != acct.current_balance) {
                                Text("Avail: ${moneyFmt.format(acct.available_balance)}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }
        }

        if (state.transactions.isNotEmpty()) {
            item { Text("Recent Transactions (30d)", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 8.dp)) }
            items(state.transactions.take(50)) { txn ->
                val isDebit = txn.amount > 0
                Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(txn.name, style = MaterialTheme.typography.bodyMedium, maxLines = 1)
                        Text("${txn.category} · ${txn.date}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Text(
                        "${if (isDebit) "-" else "+"}${moneyFmt.format(Math.abs(txn.amount))}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (isDebit) MaterialTheme.colorScheme.error else Color(0xFF2E7D32)
                    )
                }
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f))
            }
        }
    }
}
