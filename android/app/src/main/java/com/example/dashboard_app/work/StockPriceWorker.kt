package com.example.dashboard_app.work

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.example.dashboard_app.BuildConfig
import com.example.dashboard_app.data.db.AppDatabase
import com.example.dashboard_app.data.repository.StockRepository
import kotlinx.coroutines.flow.first
import java.util.concurrent.TimeUnit

class StockPriceWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val db = AppDatabase.getInstance(applicationContext)
        val repo = StockRepository(db.stockDao())
        val stocks = repo.stocks.first()
        val apiKey = BuildConfig.ALPHA_VANTAGE_KEY
        // Refresh each ticker sequentially — free tier is 25 calls/day
        stocks.forEach { stock -> repo.refreshPrice(stock, apiKey) }
        return Result.success()
    }

    companion object {
        private const val WORK_NAME = "stock_price_refresh"

        fun schedule(context: Context) {
            val request = PeriodicWorkRequestBuilder<StockPriceWorker>(6, TimeUnit.HOURS)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request
            )
        }
    }
}
