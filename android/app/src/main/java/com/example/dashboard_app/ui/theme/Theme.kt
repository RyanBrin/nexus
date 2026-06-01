package com.example.dashboard_app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

// Nexus is always dark — no light mode, no dynamic color
private val NexusColorScheme = darkColorScheme(
    primary              = NexusBlue,
    onPrimary            = NexusBg,
    primaryContainer     = NexusSurface2,
    onPrimaryContainer   = NexusBlue,

    secondary            = NexusPurple,
    onSecondary          = NexusBg,
    secondaryContainer   = NexusSurface2,
    onSecondaryContainer = NexusPurple,

    tertiary             = NexusCyan,
    onTertiary           = NexusBg,

    background           = NexusBg,
    onBackground         = NexusOnBg,

    surface              = NexusSurface,
    onSurface            = NexusOnBg,
    surfaceVariant       = NexusSurface2,
    onSurfaceVariant     = NexusMuted,

    outline              = NexusSurface2,
    outlineVariant       = NexusSurface3,

    error                = NexusRed,
    onError              = NexusOnBg,
    errorContainer       = NexusSurface,
    onErrorContainer     = NexusRed,
)

@Composable
fun DashboardappTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = NexusColorScheme,
        typography  = Typography,
        content     = content
    )
}
