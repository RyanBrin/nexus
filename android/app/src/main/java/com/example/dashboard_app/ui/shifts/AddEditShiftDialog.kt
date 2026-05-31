package com.example.dashboard_app.ui.shifts

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.dashboard_app.data.model.WorkShift
import java.text.SimpleDateFormat
import java.util.*

private val employers = listOf("Pebble Creek", "Best Buy")
private val sdf = SimpleDateFormat("MM/dd/yyyy h:mm a", Locale.US)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddEditShiftDialog(
    initial: WorkShift?,
    onDismiss: () -> Unit,
    onSave: (id: Int, employer: String, title: String, startTime: Long, endTime: Long, notes: String) -> Unit
) {
    val now = System.currentTimeMillis()
    var employer by remember { mutableStateOf(initial?.employer ?: employers[0]) }
    var title by remember { mutableStateOf(initial?.title ?: "") }
    var startTime by remember { mutableLongStateOf(initial?.startTime ?: now) }
    var endTime by remember { mutableLongStateOf(initial?.endTime ?: (now + 7 * 60 * 60 * 1000L)) }
    var notes by remember { mutableStateOf(initial?.notes ?: "") }
    var employerExpanded by remember { mutableStateOf(false) }

    // Preset shift types per employer
    val pebblePresets = listOf("Closing (2:30p–9:30p)", "Opening (6:30a–2:30p)", "Float (10a–6p)", "Custom")
    val bestBuyPresets = listOf("Host", "Product Flow", "Custom")
    val presets = if (employer == "Pebble Creek") pebblePresets else bestBuyPresets
    var selectedPreset by remember { mutableStateOf(presets[0]) }
    var presetExpanded by remember { mutableStateOf(false) }

    fun applyPreset(preset: String, base: Long) {
        val cal = Calendar.getInstance().apply { timeInMillis = base }
        when (preset) {
            "Closing (2:30p–9:30p)" -> {
                cal.set(Calendar.HOUR_OF_DAY, 14); cal.set(Calendar.MINUTE, 30)
                startTime = cal.timeInMillis
                cal.set(Calendar.HOUR_OF_DAY, 21); cal.set(Calendar.MINUTE, 30)
                endTime = cal.timeInMillis
                title = "Closing"
            }
            "Opening (6:30a–2:30p)" -> {
                cal.set(Calendar.HOUR_OF_DAY, 6); cal.set(Calendar.MINUTE, 30)
                startTime = cal.timeInMillis
                cal.set(Calendar.HOUR_OF_DAY, 14); cal.set(Calendar.MINUTE, 30)
                endTime = cal.timeInMillis
                title = "Opening"
            }
            "Float (10a–6p)" -> {
                cal.set(Calendar.HOUR_OF_DAY, 10); cal.set(Calendar.MINUTE, 0)
                startTime = cal.timeInMillis
                cal.set(Calendar.HOUR_OF_DAY, 18); cal.set(Calendar.MINUTE, 0)
                endTime = cal.timeInMillis
                title = "Float"
            }
            "Host" -> { title = "Host" }
            "Product Flow" -> { title = "Product Flow" }
        }
    }

    // Date picker state
    var showDatePicker by remember { mutableStateOf(false) }
    val datePickerState = rememberDatePickerState(initialSelectedDateMillis = startTime)

    if (showDatePicker) {
        DatePickerDialog(
            onDismissRequest = { showDatePicker = false },
            confirmButton = {
                TextButton(onClick = {
                    datePickerState.selectedDateMillis?.let { selected ->
                        val cal = Calendar.getInstance().apply { timeInMillis = startTime }
                        val dateCal = Calendar.getInstance().apply { timeInMillis = selected }
                        cal.set(dateCal.get(Calendar.YEAR), dateCal.get(Calendar.MONTH), dateCal.get(Calendar.DAY_OF_MONTH))
                        val diff = endTime - startTime
                        startTime = cal.timeInMillis
                        endTime = startTime + diff
                    }
                    showDatePicker = false
                }) { Text("OK") }
            },
            dismissButton = { TextButton(onClick = { showDatePicker = false }) { Text("Cancel") } }
        ) { DatePicker(state = datePickerState) }
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (initial == null) "Add Shift" else "Edit Shift") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                // Employer picker
                ExposedDropdownMenuBox(expanded = employerExpanded, onExpandedChange = { employerExpanded = it }) {
                    OutlinedTextField(
                        value = employer,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Employer") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = employerExpanded) },
                        modifier = Modifier.menuAnchor(MenuAnchorType.PrimaryNotEditable).fillMaxWidth()
                    )
                    ExposedDropdownMenu(expanded = employerExpanded, onDismissRequest = { employerExpanded = false }) {
                        employers.forEach { e ->
                            DropdownMenuItem(text = { Text(e) }, onClick = {
                                employer = e
                                selectedPreset = if (e == "Pebble Creek") pebblePresets[0] else bestBuyPresets[0]
                                applyPreset(selectedPreset, startTime)
                                employerExpanded = false
                            })
                        }
                    }
                }

                // Preset picker
                ExposedDropdownMenuBox(expanded = presetExpanded, onExpandedChange = { presetExpanded = it }) {
                    OutlinedTextField(
                        value = selectedPreset,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Shift type") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = presetExpanded) },
                        modifier = Modifier.menuAnchor(MenuAnchorType.PrimaryNotEditable).fillMaxWidth()
                    )
                    ExposedDropdownMenu(expanded = presetExpanded, onDismissRequest = { presetExpanded = false }) {
                        presets.forEach { p ->
                            DropdownMenuItem(text = { Text(p) }, onClick = {
                                selectedPreset = p
                                applyPreset(p, startTime)
                                presetExpanded = false
                            })
                        }
                    }
                }

                // Title (editable after preset)
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Title") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )

                // Date
                OutlinedTextField(
                    value = SimpleDateFormat("EEE, MMM d yyyy", Locale.US).format(Date(startTime)),
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Date") },
                    modifier = Modifier.fillMaxWidth(),
                    trailingIcon = {
                        TextButton(onClick = { showDatePicker = true }) { Text("Change") }
                    }
                )

                // Start / end times display
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Start: ${SimpleDateFormat("h:mm a", Locale.US).format(Date(startTime))}", style = MaterialTheme.typography.bodySmall)
                    Text("End: ${SimpleDateFormat("h:mm a", Locale.US).format(Date(endTime))}", style = MaterialTheme.typography.bodySmall)
                }

                // Notes
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
                enabled = title.isNotBlank(),
                onClick = { onSave(initial?.id ?: 0, employer, title.trim(), startTime, endTime, notes.trim()) }
            ) { Text("Save") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}
