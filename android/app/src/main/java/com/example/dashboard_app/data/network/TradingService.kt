package com.example.dashboard_app.data.network

import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Query

data class TradingStatus(
    val status: String,
    val last_tick: String?,
    val trade_count: Int,
    val last_price: Double?,
    val last_score: Double?,
    val open_trade: Map<String, Any>?,
    val strategy: String?
)

data class TradingTrade(
    val asset: String?,
    val direction: String?,
    val entry_price: Double?,
    val exit_price: Double?,
    val pnl_pct: Double?,
    val entry_ts: String?,
    val exit_ts: String?,
    val exit_reason: String?,
    val strategy_version: String?,
    val source: String?
)

interface TradingService {
    @GET("status")
    suspend fun getStatus(): TradingStatus

    @GET("trades")
    suspend fun getTrades(): List<TradingTrade>

    companion object {
        val instance: TradingService by lazy {
            Retrofit.Builder()
                .baseUrl("https://hermes-trading-production-c312.up.railway.app/")
                .client(OkHttpClient.Builder().build())
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(TradingService::class.java)
        }
    }
}
