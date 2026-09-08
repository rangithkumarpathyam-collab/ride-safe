import com.android.build.gradle.AppExtension

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
