package com.example.dashboard_app.ui.shifts

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.dashboard_app.data.model.WorkShift
import java.text.SimpleDateFormat
import java.util.*

private val pebbleColor = Color(0xFF2E7D32)
private val bestBuyColor = Color(0xFF1565C0)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShiftsScreen(vm: ShiftsViewModel = viewModel(), embedded: Boolean = false) {
    val shifts by vm.shifts.collectAsStateWithLifecycle()
    val now = System.currentTimeMillis()

    var showDialog by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf<WorkShift?>(null) }
    var deleteTarget by remember { mutableStateOf<WorkShift?>(null) }

    val upcoming = shifts.filter { it.endTime >= now }.sortedBy { it.startTime }
    val past = shifts.filter { it.endTime < now }.sortedByDescending { it.startTime }

    if (showDialog) {
        AddEditShiftDialog(
            initial = editing,
            onDismiss = { showDialog = false; editing = null },
            onSave = { id, employer, title, start, end, notes ->
                vm.save(id, employer, title, start, end, notes)
                showDialog = false; editing = null
            }
        )
    }

    deleteTarget?.let { target ->
        AlertDialog(
            onDismissRequest = { deleteTarget = null },
            title = { Text("Delete shift?") },
            text = { Text("${target.employer} — ${target.title} on ${formatDate(target.startTime)}") },
            confirmButton = {
                TextButton(onClick = { vm.delete(target); deleteTarget = null }) { Text("Delete", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = { TextButton(onClick = { deleteTarget = null }) { Text("Cancel") } }
        )
    }

    Scaffold(
        topBar = if (embedded) ({ }) else ({ TopAppBar(title = { Text("Work Shifts") }) }),
        floatingActionButton = {
            FloatingActionButton(onClick = { editing = null; showDialog = true }) {
                Icon(Icons.Default.Add, contentDescription = "Add shift")
            }
        }
    ) { padding ->
        if (shifts.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text("No shifts yet — tap + to add one.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        } else {
            LazyColumn(
                Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                contentPadding = PaddingValues(vertical = 12.dp)
            ) {
                if (upcoming.isNotEmpty()) {
                    item {
                        Text("Upcoming", style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(vertical = 4.dp))
                    }
                    items(upcoming, key = { it.id }) { shift ->
                        ShiftCard(shift, onEdit = { editing = it; showDialog = true }, onDelete = { deleteTarget = it })
                    }
                }
                if (past.isNotEmpty()) {
                    item {
                        Spacer(Modifier.height(4.dp))
                        Text("Past", style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(vertical = 4.dp))
                    }
                    items(past, key = { it.id }) { shift ->
                        ShiftCard(shift, onEdit = { editing = it; showDialog = true }, onDelete = { deleteTarget = it }, dimmed = true)
                    }
                }
            }
        }
    }
}

@Composable
private fun ShiftCard(shift: WorkShift, onEdit: (WorkShift) -> Unit, onDelete: (WorkShift) -> Unit, dimmed: Boolean = false) {
    val accentColor = if (shift.employer == "Pebble Creek") pebbleColor else bestBuyColor
    val alpha = if (dimmed) 0.5f else 1f

    ElevatedCard(Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            // Color bar
            Surface(
                modifier = Modifier.width(4.dp).height(56.dp),
                color = accentColor.copy(alpha = alpha),
                shape = MaterialTheme.shapes.small
            ) {}

            Spacer(Modifier.width(12.dp))

            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(shift.title, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = alpha))
                    Surface(color = accentColor.copy(alpha = alpha * 0.15f), shape = MaterialTheme.shapes.extraSmall) {
                        Text(shift.employer, style = MaterialTheme.typography.labelSmall,
                            color = accentColor.copy(alpha = alpha), modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp))
                    }
                }
                Spacer(Modifier.height(2.dp))
                Text(formatDate(shift.startTime), style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary.copy(alpha = alpha))
                Text("${formatTime(shift.startTime)} – ${formatTime(shift.endTime)}  (${durationHours(shift.startTime, shift.endTime)}h)",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = alpha))
                if (shift.notes.isNotBlank()) {
                    Text(shift.notes, style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = alpha * 0.7f))
                }
            }

            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                IconButton(onClick = { onEdit(shift) }) { Icon(Icons.Default.Edit, "Edit", tint = MaterialTheme.colorScheme.onSurfaceVariant) }
                IconButton(onClick = { onDelete(shift) }) { Icon(Icons.Default.Delete, "Delete", tint = MaterialTheme.colorScheme.error.copy(alpha = alpha)) }
            }
        }
    }
}

private fun formatDate(ms: Long) = SimpleDateFormat("EEE, MMM d yyyy", Locale.US).format(Date(ms))
private fun formatTime(ms: Long) = SimpleDateFormat("h:mm a", Locale.US).format(Date(ms))
private fun durationHours(start: Long, end: Long): String {
    val mins = (end - start) / 60_000
    return if (mins % 60 == 0L) "${mins / 60}" else "${mins / 60}.${(mins % 60 * 10 / 60)}"
}
