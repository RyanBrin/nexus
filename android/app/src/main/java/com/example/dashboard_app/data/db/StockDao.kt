package com.example.dashboard_app.data.db

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Query
import androidx.room.Upsert
import com.example.dashboard_app.data.model.StockItem
import kotlinx.coroutines.flow.Flow

@Dao
interface StockDao {
    @Query("SELECT * FROM stocks ORDER BY ticker ASC")
    fun getAll(): Flow<List<StockItem>>

    @Upsert
    suspend fun upsert(stock: StockItem)

    @Delete
    suspend fun delete(stock: StockItem)
}
