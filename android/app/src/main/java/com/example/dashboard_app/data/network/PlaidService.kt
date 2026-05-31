package com.example.dashboard_app.data.network

import com.example.dashboard_app.BuildConfig
import com.google.gson.annotations.SerializedName
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

data class LinkTokenResponse(val link_token: String)
data class ExchangeTokenBody(val public_token: String)
data class ExchangeTokenResponse(val ok: Boolean, val item_id: String)

data class PlaidAccount(
    val account_id: String,
    val name: String,
    val official_name: String?,
    val type: String,
    val subtype: String,
    val current_balance: Double?,
    val available_balance: Double?,
    val currency: String
)
data class AccountsResponse(val accounts: List<PlaidAccount>, val message: String? = null)

data class PlaidTransaction(
    val transaction_id: String,
    val date: String,
    val name: String,
    val amount: Double,
    val category: String,
    val account_id: String,
    val pending: Boolean
)
data class TransactionsResponse(val transactions: List<PlaidTransaction>, val count: Int = 0, val message: String? = null)

interface PlaidService {
    @POST("plaid/create_link_token")
    suspend fun createLinkToken(): LinkTokenResponse

    @POST("plaid/exchange_token")
    suspend fun exchangeToken(@Body body: ExchangeTokenBody): ExchangeTokenResponse

    @GET("plaid/accounts")
    suspend fun getAccounts(): AccountsResponse

    @GET("plaid/transactions")
    suspend fun getTransactions(@Query("days") days: Int = 30): TransactionsResponse

    companion object {
        val instance: PlaidService by lazy {
            Retrofit.Builder()
                .baseUrl(BuildConfig.DASHBOARD_API_URL + "/")
                .client(OkHttpClient.Builder().build())
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(PlaidService::class.java)
        }
    }
}
