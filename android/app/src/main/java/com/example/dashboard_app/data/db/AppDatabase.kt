package com.example.dashboard_app.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.example.dashboard_app.data.model.BudgetGoal
import com.example.dashboard_app.data.model.CreditCard
import com.example.dashboard_app.data.model.Event
import com.example.dashboard_app.data.model.StockItem
import com.example.dashboard_app.data.model.Transaction
import com.example.dashboard_app.data.model.WorkShift

@Database(
    entities = [Event::class, Transaction::class, CreditCard::class, StockItem::class, WorkShift::class, BudgetGoal::class],
    version = 5,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {

    abstract fun eventDao(): EventDao
    abstract fun transactionDao(): TransactionDao
    abstract fun creditCardDao(): CreditCardDao
    abstract fun stockDao(): StockDao
    abstract fun workShiftDao(): WorkShiftDao
    abstract fun budgetGoalDao(): BudgetGoalDao

    companion object {
        @Volatile private var INSTANCE: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "dashboard.db"
                )
                    .fallbackToDestructiveMigration(dropAllTables = true)
                    .build().also { INSTANCE = it }
            }
    }
}
