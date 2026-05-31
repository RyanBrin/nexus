package com.example.dashboard_app.data.network

import com.google.gson.annotations.SerializedName

data class GlobalQuoteResponse(
    @SerializedName("Global Quote") val globalQuote: GlobalQuote? = null,
    // Alpha Vantage returns a "Note" field when rate-limited
    @SerializedName("Note") val note: String? = null,
    @SerializedName("Information") val information: String? = null
)

data class GlobalQuote(
    @SerializedName("01. symbol") val symbol: String = "",
    @SerializedName("05. price") val price: String = "",
    @SerializedName("09. change") val change: String = "",
    @SerializedName("10. change percent") val changePercent: String = ""
)
