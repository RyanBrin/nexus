package com.example.dashboard_app.data.db

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Query
import androidx.room.Upsert
import com.example.dashboard_app.data.model.CreditCard
import kotlinx.coroutines.flow.Flow

@Dao
interface CreditCardDao {
    @Query("SELECT * FROM credit_cards ORDER BY name ASC")
    fun getAll(): Flow<List<CreditCard>>

    @Upsert
    suspend fun upsert(card: CreditCard)

    @Delete
    suspend fun delete(card: CreditCard)
}
