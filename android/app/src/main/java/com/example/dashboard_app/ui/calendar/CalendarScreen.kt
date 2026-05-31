package com.example.dashboard_app.ui.calendar

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.dashboard_app.data.model.Event
import com.example.dashboard_app.ui.shifts.ShiftsScreen
import com.example.dashboard_app.ui.shifts.ShiftsViewModel
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

private val dateFmt: DateTimeFormatter =
    DateTimeFormatter.ofPattern("EEE, MMM d • h:mm a", Locale.getDefault())

fun Long.asReadableDateTime(): String =
    Instant.ofEpochMilli(this).atZone(ZoneId.systemDefault()).format(dateFmt)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CalendarScreen(
    calendarViewModel: CalendarViewModel = viewModel(),
    shiftsViewModel: ShiftsViewModel = viewModel()
) {
    val events by calendarViewModel.events.collectAsStateWithLifecycle()
    var selectedTab by remember { mutableIntStateOf(0) }
    var editing by remember { mutableStateOf<Event?>(null) }

    Scaffold(
        topBar = { TopAppBar(title = { Text("Schedule") }) },
        floatingActionButton = {
            if (selectedTab == 0) {
                FloatingActionButton(onClick = {
                    editing = Event(title = "", dateTime = System.currentTimeMillis())
                }) { Icon(Icons.Default.Add, contentDescription = "Add event") }
            }
        }
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            PrimaryTabRow(selectedTabIndex = selectedTab) {
                Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }, text = { Text("Events") })
                Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }, text = { Text("Shifts") })
            }

            when (selectedTab) {
                0 -> EventsTab(events = events, onEdit = { editing = it }, onDelete = { calendarViewModel.deleteEvent(it) })
                1 -> ShiftsScreen(vm = shiftsViewModel, embedded = true)
            }
        }
    }

    editing?.let { current ->
        AddEditEventDialog(
            initial = current,
            onDismiss = { editing = null },
            onSave = { title, dateTime, notes ->
                calendarViewModel.saveEvent(current.id, title, dateTime, notes)
                editing = null
            }
        )
    }
}

@Composable
private fun EventsTab(
    events: List<Event>,
    onEdit: (Event) -> Unit,
    onDelete: (Event) -> Unit
) {
    if (events.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(
                "No events yet.\nTap + to add your first one.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    } else {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(events, key = { it.id }) { event ->
                EventCard(event = event, onClick = { onEdit(event) }, onDelete = { onDelete(event) })
            }
        }
    }
}

@Composable
private fun EventCard(event: Event, onClick: () -> Unit, onDelete: () -> Unit) {
    Card(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(event.title, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(4.dp))
                Text(
                    event.dateTime.asReadableDateTime(),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary
                )
                if (event.notes.isNotBlank()) {
                    Spacer(Modifier.height(4.dp))
                    Text(
                        event.notes,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
            IconButton(onClick = onDelete) {
                Icon(Icons.Default.DeleteOutline, contentDescription = "Delete event")
            }
        }
    }
}
