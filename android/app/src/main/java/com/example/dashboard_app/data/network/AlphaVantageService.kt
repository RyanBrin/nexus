package com.example.dashboard_app.data.network

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Query

interface AlphaVantageService {

    @GET("query")
    suspend fun getQuote(
        @Query("function") function: String = "GLOBAL_QUOTE",
        @Query("symbol") symbol: String,
        @Query("apikey") apiKey: String
    ): GlobalQuoteResponse

    companion object {
        private const val BASE_URL = "https://www.alphavantage.co/"

        fun create(): AlphaVantageService = Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AlphaVantageService::class.java)
    }
}
