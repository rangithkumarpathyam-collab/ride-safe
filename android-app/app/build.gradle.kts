plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.saferide.rider"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.saferide.rider"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
        // Local network / Wi-Fi IP of the host machine running the FastAPI backend
        buildConfigField("String", "API_BASE_URL", "\"http://10.88.216.167:8000\"")
        buildConfigField("String", "API_TOKEN", "\"\"")
        buildConfigField("String", "EMERGENCY_PHONE", "\"+917416960828\"")
    }

    buildFeatures {
        buildConfig = true
    }
}

kotlin {
    jvmToolchain(17)
}
