# SafeRide Rider Android App

Native Android companion for SafeRide. The app reads accelerometer, gyroscope, and GPS signals locally and presents a rider-friendly confidence score with an SOS action.

## Open and run

1. Install Android Studio with Android SDK 35 and JDK 17.
2. Open this `android-app` folder in Android Studio.
3. In **Settings > Build, Execution, Deployment > Build Tools > Gradle**, use the project Gradle wrapper and JDK 17.
4. Allow Gradle sync to download Gradle 8.9, the Android Gradle Plugin, and the Kotlin plugin.
5. Connect an Android phone or start an emulator.
6. Run the `app` configuration.
7. Allow location permission when prompted.

After location changes, always use **Build > Rebuild Project** and run the app again. The updated rider app now uses GPS and network location providers, applies a last-known location immediately, shows `LIVE` beside a valid coordinate, and opens phone location settings from the Settings tab.

The project is pinned to Gradle 8.9 because Android Gradle Plugin 8.7.3 is not compatible with the Gradle 9.3 fallback. If sync times out, retry on a stable connection or configure an HTTP proxy in Android Studio's Gradle settings.

## API connection

The Android SOS action posts to `/api/v1/incidents`. Once accepted, the app sends the latest GPS position to `/api/v1/incidents/{incident_id}/location` every five seconds while the app is in the foreground. Update these fields in `app/build.gradle.kts` for the machine running the Python API:

```kotlin
// USB-connected physical phone with adb reverse:
buildConfigField("String", "API_BASE_URL", "\"http://127.0.0.1:8000\"")
// Android Emulator: use http://10.0.2.2:8000 instead.
// Physical phone over Wi-Fi: use the computer's Wi-Fi IP instead.
buildConfigField("String", "API_TOKEN", "\"your-local-token\"")
```

Start the API from the repository root with:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

The current server accepts local requests without a token when `SAFERIDE_API_TOKEN` is unset. Set that environment variable before using the app outside a trusted local network.

Live tracking currently runs while the Android app is open. Background tracking requires a foreground location service and Android's background-location permission flow.
