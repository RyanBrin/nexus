package com.example.dashboard_app

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ShowChart
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Paid
import androidx.compose.material.icons.filled.ShowChart
import androidx.compose.material.icons.filled.Work
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.example.dashboard_app.ui.budget.BudgetScreen
import com.example.dashboard_app.ui.calendar.CalendarScreen
import com.example.dashboard_app.ui.home.HomeScreen
import com.example.dashboard_app.ui.settings.SettingsScreen
import com.example.dashboard_app.ui.shifts.ShiftsScreen
import com.example.dashboard_app.ui.stocks.StocksScreen
import com.example.dashboard_app.ui.trading.TradingScreen

enum class Dest(val route: String, val label: String, val icon: ImageVector) {
    Home("home", "Home", Icons.Default.Home),
    Calendar("calendar", "Calendar", Icons.Default.CalendarMonth),
    Budget("budget", "Budget", Icons.Default.Paid),
    Shifts("shifts", "Shifts", Icons.Default.Work),
    Trading("trading", "Trading", Icons.Default.ShowChart)
}

@Composable
fun DashboardBottomBar(navController: NavHostController) {
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    NavigationBar {
        Dest.entries.forEach { dest ->
            NavigationBarItem(
                selected = currentRoute == dest.route,
                onClick = {
                    navController.navigate(dest.route) {
                        popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                        launchSingleTop = true
                        restoreState = true
                    }
                },
                icon = { Icon(dest.icon, contentDescription = dest.label) },
                label = { Text(dest.label) }
            )
        }
    }
}

@Composable
fun DashboardNavHost(navController: NavHostController) {
    NavHost(navController = navController, startDestination = Dest.Home.route) {
        composable(Dest.Home.route) { HomeScreen(navController = navController) }
        composable(Dest.Calendar.route) { CalendarScreen() }
        composable(Dest.Budget.route) { BudgetScreen() }
        composable(Dest.Shifts.route) { ShiftsScreen() }
        composable(Dest.Trading.route) { TradingScreen() }
        composable("stocks") { StocksScreen() }
        composable("settings") { SettingsScreen() }
    }
}
