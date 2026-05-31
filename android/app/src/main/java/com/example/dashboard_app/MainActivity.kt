package com.example.dashboard_app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.navigation.compose.rememberNavController
import com.example.dashboard_app.ui.theme.DashboardappTheme
import com.example.dashboard_app.work.EventReminderWorker
import com.example.dashboard_app.work.StockPriceWorker

class MainActivity : ComponentActivity() {

    private val notifPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { /* user decision — worker fires regardless, OS silences if denied */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        StockPriceWorker.schedule(this)
        EventReminderWorker.schedule(this)
        requestNotificationPermissionIfNeeded()
        setContent { DashboardApp() }
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            notifPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}

@Composable
fun DashboardApp() {
    DashboardappTheme {
        val navController = rememberNavController()
        Scaffold(bottomBar = { DashboardBottomBar(navController) }) { padding ->
            Box(Modifier.padding(padding)) {
                DashboardNavHost(navController)
            }
        }
    }
}
