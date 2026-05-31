plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    // KSP runs Room's annotation processor. 2.2.10-2.0.2 is the version AGP 9's
    // built-in Kotlin (2.2.10) expects — using anything lower gets auto-upgraded to this.
    id("com.google.devtools.ksp") version "2.2.10-2.0.2"
}

android {
    namespace = "com.example.dashboard_app"
    compileSdk {
        version = release(36) {
            minorApiLevel = 1
        }
    }

    defaultConfig {
        applicationId = "com.example.dashboard_app"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "ALPHA_VANTAGE_KEY",
            "\"${project.findProperty("ALPHA_VANTAGE_KEY") ?: ""}\"")
        buildConfigField("String", "DASHBOARD_API_URL",
            "\"https://dashboard-api-production-ebee.up.railway.app\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }

}

dependencies {
    // --- Original wizard dependencies (unchanged) ---
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)

    // --- Added for Phase 1 (Calendar + Room + Navigation) ---
    // Direct coordinates so your libs.versions.toml stays untouched. You can
    // migrate these into the version catalog later as a tidy-up exercise.

    // ViewModel + collectAsStateWithLifecycle. Pinned to 2.6.1 to match the
    // lifecycle-runtime-ktx version already resolved by the catalog (no skew).
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.6.1")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.6.1")

    // Bottom-nav navigation between the four screens
    implementation("androidx.navigation:navigation-compose:2.9.7")

    // Extended Material icons (CalendarMonth, Paid, ShowChart, DeleteOutline…); version from the BOM
    implementation("androidx.compose.material:material-icons-extended")

    // Room local database
    implementation("androidx.room:room-runtime:2.8.4")
    implementation("androidx.room:room-ktx:2.8.4")
    ksp("androidx.room:room-compiler:2.8.4")

    // Encrypted storage — for OAuth tokens in Phase 2 (Outlook sync)
    implementation("androidx.security:security-crypto:1.1.0")

    // Retrofit + OkHttp — Phase 2 live stock prices
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // WorkManager — background price refresh + event reminders
    implementation("androidx.work:work-runtime-ktx:2.10.1")

    // Plaid Link SDK — bank account connection UI
    implementation("com.plaid.link:sdk-core:4.1.0")

    // --- Test dependencies (unchanged) ---
    testImplementation(libs.junit)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}
