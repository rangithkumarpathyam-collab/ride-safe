import com.android.build.gradle.AppExtension

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

import java.util.Properties

val envProperties = Properties().apply {
    val envFile = rootProject.file("../.env")
    if (envFile.exists()) {
        envFile.forEachLine { line ->
            val trimmed = line.trim()
            if (trimmed.isNotEmpty() && !trimmed.startsWith("#") && trimmed.contains("=")) {
                val idx = trimmed.indexOf('=')
                val key = trimmed.substring(0, idx).trim()
                val value = trimmed.substring(idx + 1).trim()
                setProperty(key, value)
            }
        }
    }
}

val twilioSid = envProperties.getProperty("TWILIO_ACCOUNT_SID") ?: ""
val twilioToken = envProperties.getProperty("TWILIO_AUTH_TOKEN") ?: ""
val twilioFrom = envProperties.getProperty("TWILIO_PHONE_NUMBER") ?: ""
val emergencyPhone = envProperties.getProperty("EMERGENCY_DISPATCH_PHONE") ?: "+917416960828"
val apiToken = envProperties.getProperty("SAFERIDE_API_TOKEN") ?: ""
val apiBaseUrl = envProperties.getProperty("API_BASE_URL") ?: "https://your-backend-service.onrender.com"

android {
    namespace = "com.saferide.rider"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.saferide.rider"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
        // Cloud-hosted FastAPI backend URL, or a local override if the developer set one.
        buildConfigField("String", "API_BASE_URL", "\"$apiBaseUrl\"")
        buildConfigField("String", "API_TOKEN", "\"$apiToken\"")
        buildConfigField("String", "EMERGENCY_PHONE", "\"$emergencyPhone\"")
        buildConfigField("String", "TWILIO_ACCOUNT_SID", "\"$twilioSid\"")
        buildConfigField("String", "TWILIO_AUTH_TOKEN", "\"$twilioToken\"")
        buildConfigField("String", "TWILIO_PHONE_NUMBER", "\"$twilioFrom\"")
    }

    buildFeatures {
        buildConfig = true
    }
}

kotlin {
    jvmToolchain(17)
}

val setupAdbReverse = tasks.register<Exec>("setupAdbReverse") {
    description = "Forward host API port 8000 to connected USB device"
    val adb = (project.extensions.getByName("android") as AppExtension).adbExecutable.absolutePath
    commandLine(adb, "reverse", "tcp:8000", "tcp:8000")
    isIgnoreExitValue = true
    doLast {
        println("SafeRide: Configured adb reverse tcp:8000 tcp:8000")
    }
}

tasks.matching { it.name.startsWith("install") || it.name.startsWith("assemble") }.configureEach {
    finalizedBy(setupAdbReverse)
}
