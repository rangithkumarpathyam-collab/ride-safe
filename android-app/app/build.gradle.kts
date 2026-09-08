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
        // USB-connected physical phone uses adb reverse to reach the host API.
        buildConfigField("String", "API_BASE_URL", "\"http://127.0.0.1:8000\"")
        buildConfigField("String", "API_TOKEN", "\"\"")
    }

    buildFeatures {
        buildConfig = true
    }
}

kotlin {
    jvmToolchain(17)
}
