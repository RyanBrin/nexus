package com.example.dashboard_app.ui.calendar

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.example.dashboard_app.data.model.Event
import java.time.Instant
import java.time.LocalTime
import java.time.ZoneId

/**
 * Add/Edit dialog. Demonstrates Compose state hoisting + Material3 pickers +
 * basic input validation (Save is disabled while the title is blank).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddEditEventDialog(
    initial: Event,
    onDismiss: () -> Unit,
    onSave: (title: String, dateTime: Long, notes: String) -> Unit
) {
    var title by remember { mutableStateOf(initial.title) }
    var notes by remember { mutableStateOf(initial.notes) }
    var dateTimeMillis by remember { mutableLongStateOf(initial.dateTime) }

    var showDatePicker by remember { mutableStateOf(false) }
    var showTimePicker by remember { mutableStateOf(false) }

    val isNew = initial.id == 0
    val titleValid = title.isNotBlank()

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (isNew) "New event" else "Edit event") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Title") },
                    singleLine = true,
                    isError = !titleValid,
                    supportingText = { if (!titleValid) Text("Title is required") },
                    modifier = Modifier.fillMaxWidth()
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { showDatePicker = true }, modifier = Modifier.weight(1f)) {
                        Text("Date")
                    }
                    OutlinedButton(onClick = { showTimePicker = true }, modifier = Modifier.weight(1f)) {
                        Text("Time")
                    }
                }
                Text(
                    dateTimeMillis.asReadableDateTime(),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary
                )
                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text("Notes (optional)") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 2
                )
            }
        },
        confirmButton = {
            TextButton(
                enabled = titleValid,
                onClick = { onSave(title, dateTimeMillis, notes) }
            ) { Text("Save") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )

    if (showDatePicker) {
        val state = rememberDatePickerState(initialSelectedDateMillis = dateTimeMillis)
        DatePickerDialog(
            onDismissRequest = { showDatePicker = false },
            confirmButton = {
                TextButton(onClick = {
                    state.selectedDateMillis?.let { picked ->
                        // Keep the existing time-of-day, replace the date.
                        val oldTime = Instant.ofEpochMilli(dateTimeMillis)
                            .atZone(ZoneId.systemDefault()).toLocalTime()
                        dateTimeMillis = Instant.ofEpochMilli(picked)
                            .atZone(ZoneId.systemDefault())
                            .toLocalDate()
                            .atTime(oldTime)
                            .atZone(ZoneId.systemDefault())
                            .toInstant().toEpochMilli()
                    }
                    showDatePicker = false
                }) { Text("OK") }
            },
            dismissButton = { TextButton(onClick = { showDatePicker = false }) { Text("Cancel") } }
        ) { DatePicker(state = state) }
    }

    if (showTimePicker) {
        val now = Instant.ofEpochMilli(dateTimeMillis).atZone(ZoneId.systemDefault())
        val timeState = rememberTimePickerState(
            initialHour = now.hour, initialMinute = now.minute, is24Hour = false
        )
        Dialog(onDismissRequest = { showTimePicker = false }) {
            Surface(shape = MaterialTheme.shapes.large, tonalElevation = 6.dp) {
                Column(Modifier.padding(20.dp), horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally) {
                    Text("Select time", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(16.dp))
                    TimePicker(state = timeState)
                    Spacer(Modifier.height(8.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        TextButton(onClick = { showTimePicker = false }) { Text("Cancel") }
                        TextButton(onClick = {
                            val date = Instant.ofEpochMilli(dateTimeMillis)
                                .atZone(ZoneId.systemDefault()).toLocalDate()
                            dateTimeMillis = date
                                .atTime(LocalTime.of(timeState.hour, timeState.minute))
                                .atZone(ZoneId.systemDefault())
                                .toInstant().toEpochMilli()
                            showTimePicker = false
                        }) { Text("OK") }
                    }
                }
            }
        }
    }
}
