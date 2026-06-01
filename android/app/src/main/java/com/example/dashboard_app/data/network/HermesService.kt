package com.example.dashboard_app.data.network

import com.google.gson.annotations.SerializedName
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

data class HermesStatusResponse(
    val status: Map<String, Any?>,
    val settings: Map<String, Any?>,
    val risk_rules: Map<String, Any?>,
    val idea_stats: Map<String, Any?>,
)

data class HermesTradeIdea(
    val ticker: String,
    val asset_type: String,
    val direction: String,
    val entry_price: Double?,
    val stop_price: Double?,
    val target_price: Double?,
    val risk_pct: Double?,
    val risk_reward: Double?,
    val confidence: Int,
    val strategy_version: String,
    val chart_reason: String,
    val news_summary: String,
    val news_risk: String,
    val wave_count: String,
    val fib_zone: String,
    val trend: String,
    val status: String,
    val rejection_reason: String,
    val hermes_notes: String,
    val created_at: String,
)

data class HermesIdeaStats(
    val total_ideas: Int,
    val approved: Int,
    val rejected: Int,
    val watching: Int,
    val approval_rate_pct: Double,
)

interface HermesService {
    @GET("hermes/status")
    suspend fun getStatus(): HermesStatusResponse

    @GET("hermes/trade-ideas")
    suspend fun getTradeIdeas(
        @Query("limit") limit: Int = 30,
        @Query("status") status: String = ""
    ): List<HermesTradeIdea>

    @GET("hermes/trade-ideas/stats")
    suspend fun getIdeaStats(): HermesIdeaStats

    @GET("hermes/risk-rules")
    suspend fun getRiskRules(): Map<String, Any?>

    @GET("hermes/logs")
    suspend fun getLogs(): Map<String, Any?>

    @PATCH("hermes/settings")
    suspend fun updateSettings(@Body settings: Map<String, Any>): Map<String, Any?>

    @GET("stocks/watchlist")
    suspend fun getWatchlist(): List<Map<String, Any?>>

    @POST("stocks/watchlist")
    suspend fun addStock(@Body body: Map<String, Any>): Map<String, Any?>

    @DELETE("stocks/watchlist/{ticker}")
    suspend fun removeStock(@Path("ticker") ticker: String): Map<String, Any?>

    @PATCH("stocks/watchlist/{ticker}/toggle")
    suspend fun toggleStock(
        @Path("ticker") ticker: String,
        @Body body: Map<String, Any>
    ): Map<String, Any?>

    companion object {
        val instance: HermesService by lazy {
            Retrofit.Builder()
                .baseUrl(com.example.dashboard_app.BuildConfig.DASHBOARD_API_URL.replace(
                    "dashboard-api-production-ebee.up.railway.app",
                    "hermes-trading-production-c312.up.railway.app"
                ) + "/")
                .client(OkHttpClient.Builder().build())
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(HermesService::class.java)
        }
    }
}
