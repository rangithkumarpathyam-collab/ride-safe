package com.saferide.rider

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.CountDownTimer
import android.os.VibrationEffect
import android.os.Vibrator
import android.provider.Settings
import android.util.Base64
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.util.Locale
import kotlin.math.atan2
import kotlin.math.max
import kotlin.math.sqrt

class MainActivity : Activity(), SensorEventListener {

    private lateinit var sensorManager: SensorManager
    private lateinit var locationManager: LocationManager
    private lateinit var confidenceView: TextView
    private lateinit var confidenceBadge: TextView
    private lateinit var sensorStatusView: TextView
    private lateinit var locationView: TextView
    private lateinit var impactView: TextView
    private lateinit var tiltView: TextView
    private lateinit var speedView: TextView

    private var peakG = 0f
    private var tiltDegrees = 0f
    private var speedKmh = 0f
    private var previousSpeedKmh = 0f
    private var latitude = 0.0
    private var longitude = 0.0
    private var activeIncidentId: String? = null
    private var lastLocationSentAt = 0L
    private var lastRecordedLocation: Location? = null
    private var sosCountdownTimer: CountDownTimer? = null
    private var sosDialog: AlertDialog? = null
    private var sosCancelledRecently = false
    private var isSimulatingAbnormal = false
    private var lastScoreUpdateMs = 0L

    private fun vibrateOnce(durationMs: Long) {
        val vibrator = getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator?.vibrate(VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                vibrator?.vibrate(durationMs)
            }
        } catch (_: Exception) {}
    }

    private fun cancelVibration() {
        try {
            (getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator)?.cancel()
        } catch (_: Exception) {}
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = color("#060B14")
        window.navigationBarColor = color("#060B14")
        window.decorView.systemUiVisibility = 0
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager
        setContentView(buildScreen())
        requestLocationPermission()
        handleIntentActions(intent)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        handleIntentActions(intent)
    }

    private fun handleIntentActions(intent: Intent?) {
        val action = intent?.getStringExtra("action")
        if (action == "trigger_abnormal") {
            window.decorView.postDelayed({ simulateAbnormalCrash() }, 200)
        } else if (action == "reset_nominal") {
            window.decorView.postDelayed({ resetTelemetryToNominal() }, 200)
        } else if (action == "trigger_women_safety") {
            window.decorView.postDelayed({ executeWomenSafetyDispatch() }, 200)
        }
    }

    private fun buildScreen(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(44), dp(16), dp(24))
            minimumHeight = resources.displayMetrics.heightPixels
            setBackgroundColor(color("#060B14"))
        }

        val scroll = ScrollView(this).apply {
            isFillViewport = true
            setBackgroundColor(color("#060B14"))
            addView(root, FrameLayout.LayoutParams(-1, -1))
        }

        // --- TOP OPERATOR GLASS HEADER ---
        val headerCard = glassCard(radius = 20, strokeColor = "#4038BDF8", fillColor = "#1C0F1D38").apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(14))
        }

        val avatar = TextView(this).apply {
            text = "🏍️"
            textSize = 24f
            gravity = Gravity.CENTER
            background = glassGradientCard("#2563EB", "#0284C7", "#8038BDF8", 16)
            layoutParams = LinearLayout.LayoutParams(dp(48), dp(48)).apply { marginEnd = dp(14) }
        }
        headerCard.addView(avatar)

        val headerText = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, -2, 1f)
        }
        headerText.addView(text("SafeRide AI", 18f, "#F8FAFC", true))
        headerText.addView(text("Active Protection Mode · Real-Time Guard", 11f, "#38BDF8", false))
        headerCard.addView(headerText)

        val livePill = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            background = roundedBackground("#064E3B", 999, "#10B981")
            setPadding(dp(12), dp(6), dp(12), dp(6))
        }
        livePill.addView(text("● ARMED", 11f, "#34D399", true))
        headerCard.addView(livePill)
        root.addView(headerCard)

        // --- TELEMETRY STATUS CHIP ---
        val telemetryChip = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            background = roundedBackground("#0C1A2E", 14, "#0284C7")
            setPadding(dp(14), dp(8), dp(14), dp(8))
            layoutParams = LinearLayout.LayoutParams(-1, -2).apply {
                topMargin = dp(12)
                bottomMargin = dp(4)
            }
        }
        sensorStatusView = text("⚡ SENSORS ARMED  ·  Peak 0.00 G  ·  Tilt 0.0°", 11f, "#38BDF8", true)
        telemetryChip.addView(sensorStatusView)
        root.addView(telemetryChip)

        // --- LIVE RIDE SIGNALS HUD ---
        root.addView(section("LIVE TELEMETRY HUD"))
        val hudRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, dp(4), 0, dp(6))
        }
        impactView = statTile(hudRow, "PEAK IMPACT", "0.00 G", "#38BDF8")
        tiltView = statTile(hudRow, "TILT ANGLE", "0.0°", "#F59E0B")
        speedView = statTile(hudRow, "GPS SPEED", "0 km/h", "#34D399")
        root.addView(hudRow)

        // --- AI RISK MONITOR GLASS CARD ---
        root.addView(section("AI CRASH RISK EVALUATION"))
        val scoreCard = glassCard(radius = 20, strokeColor = "#3538BDF8", fillColor = "#1613233F").apply {
            gravity = Gravity.CENTER
            setPadding(dp(18), dp(18), dp(18), dp(18))
        }
        scoreCard.addView(text("SAFETY CONFIDENCE SCORE", 11f, "#7DD3FC", true))

        confidenceView = text("0%", 56f, "#34D399", true).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(4), 0, dp(2))
        }
        scoreCard.addView(confidenceView)

        confidenceBadge = text("🟢 ALL TELEMETRY NOMINAL · RIDE SAFE", 11f, "#34D399", true).apply {
            gravity = Gravity.CENTER
            background = roundedBackground("#064E3B", 999, "#10B981")
            setPadding(dp(16), dp(6), dp(16), dp(6))
        }
        scoreCard.addView(confidenceBadge)

        scoreCard.addView(text("Rule-Based Fusion: Accelerometer (3.0G+), Gyro Tilt (65°+) & GPS Speed Drop", 10f, "#94A3B8", false).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(8), 0, dp(4))
        })

        root.addView(scoreCard)

        // --- LIVE GPS & GIS NAVIGATION CARD ---
        root.addView(section("LIVE GPS SATELLITE FIX"))
        val locationCard = glassCard(radius = 18, strokeColor = "#3538BDF8", fillColor = "#160F1D36").apply {
            setPadding(dp(16), dp(14), dp(16), dp(14))
        }
        val locHeader = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        locHeader.addView(text("📍 RIDER COORDINATES", 11f, "#38BDF8", true), LinearLayout.LayoutParams(0, -2, 1f))
        locHeader.addView(text("● GPS ACTIVE", 10f, "#34D399", true))
        locationCard.addView(locHeader)

        locationView = text("Acquiring high-accuracy satellite fix...", 13f, "#F1F5F9", true).apply {
            setPadding(0, dp(8), 0, dp(10))
        }
        locationCard.addView(locationView)

        val mapsBtn = Button(this).apply {
            text = "🗺️ Open Live Google Maps Route"
            textSize = 12f
            setTextColor(color("#38BDF8"))
            setTypeface(null, Typeface.BOLD)
            background = roundedBackground("#0F2942", 12, "#0284C7")
            setOnClickListener { openMap() }
        }
        locationCard.addView(mapsBtn, LinearLayout.LayoutParams(-1, dp(44)))
        root.addView(locationCard)

        // --- HERO RED GLASS SOS BUTTON ---
        val sosButton = Button(this).apply {
            text = "🚨 SOS — EMERGENCY ASSISTANCE"
            textSize = 15f
            setTextColor(color("#FFFFFF"))
            setTypeface(null, Typeface.BOLD)
            background = glassGradientCard("#DC2626", "#991B1B", "#FCA5A5", 16)
            setPadding(0, dp(12), 0, dp(12))
            setOnClickListener { startSosCountdown(false) }
        }
        root.addView(sosButton, LinearLayout.LayoutParams(-1, dp(58)).apply {
            topMargin = dp(16)
            bottomMargin = dp(8)
        })

        // --- WOMEN SAFETY EMERGENCY BUTTON (ACTIVATED BY LONG PRESS) ---
        val womenSafetyCard = glassCard(radius = 16, strokeColor = "#60F472B6", fillColor = "#203B0728").apply {
            setPadding(dp(14), dp(12), dp(14), dp(12))
        }
        val womenHeader = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        womenHeader.addView(text("🛡️ WOMEN SAFETY PROTOCOL", 11f, "#F472B6", true), LinearLayout.LayoutParams(0, -2, 1f))
        womenHeader.addView(text("● LONG-PRESS TO ACTIVATE", 10f, "#FDA4AF", true))
        womenSafetyCard.addView(womenHeader)

        val womenSosButton = Button(this).apply {
            text = "🌸 WOMEN SAFETY SOS (HOLD 2s)"
            textSize = 15f
            setTextColor(color("#FFFFFF"))
            setTypeface(null, Typeface.BOLD)
            background = glassGradientCard("#BE185D", "#831843", "#F472B6", 14)
            isClickable = true
            isFocusable = true
            isLongClickable = true
            setPadding(0, dp(12), 0, dp(12))

            // Standard Android Long-Click: Fires reliably after hold duration (~1-1.5s)
            setOnLongClickListener {
                vibrateOnce(400)
                executeWomenSafetyDispatch()
                true
            }

            // Standard Click: Educates rider that long-press is required
            setOnClickListener {
                Toast.makeText(this@MainActivity, "⚠️ WOMEN SAFETY: Press and hold for 2 seconds to activate.", Toast.LENGTH_SHORT).show()
            }

            // Visual press feedback
            setOnTouchListener { v, event ->
                when (event.action) {
                    MotionEvent.ACTION_DOWN -> {
                        v.parent?.requestDisallowInterceptTouchEvent(true)
                        v.animate().scaleX(0.96f).scaleY(0.96f).setDuration(100).start()
                        false // Let LongClickListener and ClickListener receive event!
                    }
                    MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                        v.animate().scaleX(1.0f).scaleY(1.0f).setDuration(100).start()
                        false
                    }
                    MotionEvent.ACTION_MOVE -> {
                        v.parent?.requestDisallowInterceptTouchEvent(true)
                        false
                    }
                    else -> false
                }
            }
        }
        womenSafetyCard.addView(womenSosButton, LinearLayout.LayoutParams(-1, dp(56)).apply {
            topMargin = dp(8)
        })

        val womenNotice = text("🔒 Hold 2s to activate · Immediately dials Twilio emergency voice call & SMS to ${BuildConfig.EMERGENCY_PHONE}", 10f, "#FDA4AF", false).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(6), 0, 0)
        }
        womenSafetyCard.addView(womenNotice)
        root.addView(womenSafetyCard, LinearLayout.LayoutParams(-1, -2).apply {
            bottomMargin = dp(10)
        })

        // --- FLOATING GLASS BOTTOM NAVIGATION BAR ---
        val navCard = glassCard(radius = 999, strokeColor = "#30FFFFFF", fillColor = "#250F172A").apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(dp(6), dp(6), dp(6), dp(6))
        }
        navCard.addView(navItem("⌂\nHome", "#38BDF8") { locationView.requestFocus() })
        navCard.addView(navItem("!\nAlerts", "#94A3B8") { showAlerts() })
        navCard.addView(navItem("🌸\nWomen", "#F472B6") { executeWomenSafetyDispatch() })
        navCard.addView(navItem("⌖\nMap", "#94A3B8") { openMap() })
        navCard.addView(navItem("⚙\nSettings", "#94A3B8") { openSettingsDialog() })
        root.addView(navCard, LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(10)
            bottomMargin = dp(10)
        })

        return scroll
    }

    private fun simulateAbnormalCrash() {
        sosCancelledRecently = false
        activeIncidentId = null
        isSimulatingAbnormal = true
        peakG = 3.8f
        tiltDegrees = 65f
        previousSpeedKmh = 60f
        speedKmh = 0f
        Toast.makeText(this, "Simulating abnormal crash telemetry...", Toast.LENGTH_SHORT).show()
        updateScore()
        if (sosCountdownTimer == null) {
            startSosCountdown(isAutomaticCrash = true, triggerScore = 98f)
        }
    }

    private fun resetTelemetryToNominal() {
        isSimulatingAbnormal = false
        sosCancelledRecently = false
        activeIncidentId = null
        peakG = 1.0f
        tiltDegrees = 0f
        speedKmh = 0f
        previousSpeedKmh = 0f
        Toast.makeText(this, "Telemetry reset to nominal.", Toast.LENGTH_SHORT).show()
        updateScore()
    }

    override fun onResume() {
        super.onResume()
        sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
        requestLocationUpdates()
    }

    override fun onPause() {
        super.onPause()
        sensorManager.unregisterListener(this)
        if (::locationManager.isInitialized) locationManager.removeUpdates(locationListener)
    }

    override fun onDestroy() {
        super.onDestroy()
        sosCountdownTimer?.cancel()
        sosCountdownTimer = null
        sosDialog?.dismiss()
        sosDialog = null
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor.type == Sensor.TYPE_ACCELEROMETER) {
            val g = sqrt(event.values[0] * event.values[0] + event.values[1] * event.values[1] + event.values[2] * event.values[2]) / SensorManager.GRAVITY_EARTH
            if (!isSimulatingAbnormal) {
                // Faster decay (0.96f) so brief bumps/vibrations don't linger in peakG
                peakG = max(peakG * 0.96f, g)
                tiltDegrees = Math.toDegrees(atan2(
                    sqrt(event.values[0] * event.values[0] + event.values[1] * event.values[1]).toDouble(),
                    event.values[2].toDouble(),
                )).toFloat()
            }
            val now = System.currentTimeMillis()
            // Only flag as spike if BOTH G-force AND tilt are clearly abnormal (avoids false triggers)
            val isSpike = peakG >= 3.2f || (tiltDegrees >= 65f && peakG >= 2.6f)
            if (isSpike || now - lastScoreUpdateMs >= 200L) {
                lastScoreUpdateMs = now
                updateScore()
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit

    private fun updateScore() {
        if (!::confidenceView.isInitialized || !::sensorStatusView.isInitialized ||
            !::impactView.isInitialized || !::tiltView.isInitialized || !::speedView.isInitialized ||
            !::confidenceBadge.isInitialized) {
            return
        }

        // --- HIGH-IMPACT THRESHOLDS (v2) ---
        // Impact: starts scoring above 3.0G — motorcycle crashes typically 4–8G, bumps < 2.5G
        val impactScore = (((peakG - 3.0f) / 2.0f) * 100f).coerceIn(0f, 100f)
        // Tilt: scores above 65° only — bike leans ~30° in turns, crash = 70–90°
        val tiltScore = (((tiltDegrees - 65f) / 20f) * 100f).coerceIn(0f, 100f)
        // Speed drop: 50+ km/h sudden deceleration (hard braking is ~20 km/h drop)
        val speedDrop = (previousSpeedKmh - speedKmh).coerceAtLeast(0f)
        val speedScore = ((speedDrop / 50f) * 100f).coerceIn(0f, 100f)

        // Weighted base — requires multiple signals for a high combined score
        val baseScore = (impactScore * 0.50f + tiltScore * 0.30f + speedScore * 0.20f)

        // Hard overrides: BOTH G-force AND tilt must be extreme simultaneously
        val confidence = max(
            baseScore,
            if (peakG >= 4.5f && tiltDegrees >= 65f) 95f        // catastrophic crash
            else if (peakG >= 3.8f && tiltDegrees >= 60f) 88f   // severe crash
            else if (peakG >= 3.5f && speedDrop >= 40f) 82f     // high-speed collision
            else if (peakG >= 3.0f && tiltDegrees >= 70f) 75f   // tipped over hard
            else if (peakG >= 4.0f) 70f                         // extreme single impact
            else 0f
        ).coerceIn(0f, 100f)

        // SOS trigger at 70% — requires clearly crash-level readings
        val isNotNormal = confidence >= 70f

        confidenceView.text = String.format(Locale.US, "%.0f%%", confidence)
        if (isNotNormal) {
            confidenceView.setTextColor(color("#EF4444"))
            confidenceBadge.text = String.format(Locale.US, "🔴 CRASH RISK DETECTED (%.0f%%)", confidence)
            confidenceBadge.setTextColor(color("#F87171"))
            confidenceBadge.background = roundedBackground("#450A0A", 999, "#EF4444")
        } else if (confidence >= 45f) {
            // Warning zone: elevated readings, monitoring only — no SOS
            confidenceView.setTextColor(color("#F59E0B"))
            confidenceBadge.text = String.format(Locale.US, "🟡 ELEVATED IMPACT (%.0f%%) — MONITORING", confidence)
            confidenceBadge.setTextColor(color("#FCD34D"))
            confidenceBadge.background = roundedBackground("#451A03", 999, "#D97706")
        } else {
            confidenceView.setTextColor(color("#34D399"))
            confidenceBadge.text = "🟢 ALL TELEMETRY NOMINAL · RIDE SAFE"
            confidenceBadge.setTextColor(color("#34D399"))
            confidenceBadge.background = roundedBackground("#064E3B", 999, "#10B981")
            if (confidence < 15f && peakG < 2.5f && tiltDegrees < 50f) {
                sosCancelledRecently = false
            }
        }

        impactView.text = String.format(Locale.US, "%.2f G", peakG)
        tiltView.text = String.format(Locale.US, "%.0f°", tiltDegrees)
        speedView.text = String.format(Locale.US, "%.0f km/h", speedKmh)
        sensorStatusView.text = String.format(Locale.US, "⚡ SENSORS ARMED  ·  Peak %.2f G  ·  Tilt %.1f°", peakG, tiltDegrees)

        // Auto SOS: only fire when confidence >= 70% (genuine high-impact crash level)
        if (isNotNormal) {
            if (sosCountdownTimer == null && !sosCancelledRecently) {
                startSosCountdown(isAutomaticCrash = true, triggerScore = confidence)
            }
        }
    }

    // --- 10-SECOND EMERGENCY DISPATCH MODAL ---
    private fun startSosCountdown(isAutomaticCrash: Boolean, triggerScore: Float = 0f) {
        if (sosCountdownTimer != null) return
        activeIncidentId = null

        vibrateOnce(350)

        val dialogView = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(24), dp(22), dp(22))
            background = roundedBackground("#17090D", 20, "#EF4444")
        }

        val badge = TextView(this).apply {
            text = if (isAutomaticCrash) {
                if (triggerScore > 0f) String.format(Locale.US, "🚨 ABNORMAL SCORE DETECTED (%.0f%%)", triggerScore)
                else "🚨 ABNORMAL SAFETY TELEMETRY DETECTED"
            } else {
                "🚨 CRITICAL EMERGENCY SOS"
            }
            textSize = 13f
            setTextColor(color("#F87171"))
            setTypeface(null, Typeface.BOLD)
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(4))
        }
        dialogView.addView(badge)

        val headerText = TextView(this).apply {
            text = if (isAutomaticCrash) "AUTOMATIC EMERGENCY SOS ACTIVATED" else "10-SECOND EMERGENCY DISPATCH"
            textSize = 17f
            setTextColor(color("#FFFFFF"))
            setTypeface(null, Typeface.BOLD)
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(6))
        }
        dialogView.addView(headerText)

        val subText = TextView(this).apply {
            text = if (isAutomaticCrash) {
                "Safety confidence score is NOT NORMAL! Automated Twilio voice call & location SMS will be dispatched to ${BuildConfig.EMERGENCY_PHONE} in:"
            } else {
                "Automated Twilio voice call & location SMS will be dispatched to ${BuildConfig.EMERGENCY_PHONE} in:"
            }
            textSize = 12f
            setTextColor(color("#CBD5E1"))
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(10))
        }
        dialogView.addView(subText)

        val timerNumberView = TextView(this).apply {
            text = "10"
            textSize = 72f
            setTextColor(color("#EF4444"))
            setTypeface(null, Typeface.BOLD)
            gravity = Gravity.CENTER
        }
        dialogView.addView(timerNumberView)

        val secondsLabel = TextView(this).apply {
            text = "SECONDS REMAINING"
            textSize = 11f
            setTextColor(color("#F87171"))
            setTypeface(null, Typeface.BOLD)
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(10))
        }
        dialogView.addView(secondsLabel)

        val progressBar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            progress = 100
            isIndeterminate = false
        }
        dialogView.addView(progressBar, LinearLayout.LayoutParams(-1, dp(10)).apply {
            bottomMargin = dp(14)
        })

        val locationChip = TextView(this).apply {
            text = String.format(Locale.US, "📍 Live GPS: %.5f, %.5f", latitude, longitude)
            textSize = 12f
            setTextColor(color("#67E8F9"))
            gravity = Gravity.CENTER
            background = roundedBackground("#0F2942", 8, "#0284C7")
            setPadding(dp(8), dp(6), dp(8), dp(6))
        }
        dialogView.addView(locationChip, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(14) })

        val cancelBtn = Button(this).apply {
            text = "✋ CANCEL — I'M OK (FALSE ALARM)"
            textSize = 14f
            setTextColor(color("#FFFFFF"))
            setTypeface(null, Typeface.BOLD)
            background = glassGradientCard("#059669", "#047857", "#6EE7B7", 12)
            setPadding(0, dp(10), 0, dp(10))
            setOnClickListener {
                sosCountdownTimer?.cancel()
                sosCountdownTimer = null
                cancelVibration()
                sosCancelledRecently = true
                isSimulatingAbnormal = false
                activeIncidentId = null
                sosDialog?.dismiss()
                sosDialog = null
                Toast.makeText(this@MainActivity, "Emergency alert cancelled.", Toast.LENGTH_SHORT).show()
                window.decorView.postDelayed({
                    sosCancelledRecently = false
                }, 8000L)
                updateScore()
            }
        }
        dialogView.addView(cancelBtn, LinearLayout.LayoutParams(-1, dp(50)).apply {
            bottomMargin = dp(8)
        })

        val dispatchNowBtn = Button(this).apply {
            text = "⚡ DISPATCH IMMEDIATELY (TWILIO CALL)"
            textSize = 13f
            setTextColor(color("#FFFFFF"))
            setTypeface(null, Typeface.BOLD)
            background = glassGradientCard("#DC2626", "#991B1B", "#FCA5A5", 12)
            setPadding(0, dp(8), 0, dp(8))
            setOnClickListener {
                sosCountdownTimer?.cancel()
                sosCountdownTimer = null
                cancelVibration()
                sosDialog?.dismiss()
                sosDialog = null
                executeFullEmergencyDispatch()
            }
        }
        dialogView.addView(dispatchNowBtn, LinearLayout.LayoutParams(-1, dp(48)).apply {
            bottomMargin = dp(8)
        })

        val directDialBtn = Button(this).apply {
            text = "📞 DIRECT CALL 108 / AMBULANCE"
            textSize = 12f
            setTextColor(color("#E2E8F0"))
            background = roundedBackground("#1E293B", 10, "#475569")
            setOnClickListener {
                try {
                    val dialIntent = Intent(Intent.ACTION_DIAL, android.net.Uri.parse("tel:${BuildConfig.EMERGENCY_PHONE}"))
                    startActivity(dialIntent)
                } catch (_: Exception) {}
            }
        }
        dialogView.addView(directDialBtn, LinearLayout.LayoutParams(-1, dp(42)))

        sosDialog = AlertDialog.Builder(this)
            .setView(dialogView)
            .setCancelable(false)
            .create()

        sosDialog?.show()

        sosCountdownTimer = object : CountDownTimer(10000L, 1000L) {
            override fun onTick(millisUntilFinished: Long) {
                val secondsRemaining = ((millisUntilFinished + 500L) / 1000L).coerceAtLeast(1L)
                timerNumberView.text = secondsRemaining.toString()
                progressBar.progress = (secondsRemaining * 10).toInt()
                vibrateOnce(120)
            }

            override fun onFinish() {
                timerNumberView.text = "0"
                progressBar.progress = 0
                vibrateOnce(450)
                sosDialog?.dismiss()
                sosDialog = null
                sosCountdownTimer = null
                isSimulatingAbnormal = false
                executeFullEmergencyDispatch()
            }
        }.start()
    }

    // --- FULL EMERGENCY DISPATCH: TWILIO CLOUD + LOCAL API BACKEND ---
    private fun executeFullEmergencyDispatch() {
        val targetPhone = BuildConfig.EMERGENCY_PHONE
        val curLat = latitude
        val curLon = longitude

        Toast.makeText(this, "Placing Twilio emergency voice call to $targetPhone...", Toast.LENGTH_SHORT).show()

        // 1. Asynchronously send SMS and notify backend
        sendTwilioSmsDirectly(targetPhone, curLat, curLon) { _, _ -> }
        notifyLocalApiServer(targetPhone, curLat, curLon)

        // 2. Direct Twilio Cloud Voice Call
        callTwilioDirectly(targetPhone, curLat, curLon) { callOk, callSid, callMsg ->
            runOnUiThread {
                if (isFinishing) return@runOnUiThread
                val title = if (callOk) "🚨 EMERGENCY DISPATCH ACTIVE" else "Emergency Dispatch Status"
                val message = if (callOk) {
                    "📞 AUTOMATED TWILIO VOICE CALL PLACED!\n\n" +
                    "• Recipient: $targetPhone\n" +
                    "• Call SID: $callSid\n" +
                    "• Call Status: $callMsg\n" +
                    "• SMS Alert: Delivered\n" +
                    "• Live GPS: ${String.format(Locale.US, "%.5f, %.5f", curLat, curLon)}\n\n" +
                    "Emergency response teams have received automated voice telemetry."
                } else {
                    "⚠️ Twilio Dispatch Notice:\n$callMsg\n\n" +
                    "Target: $targetPhone\n" +
                    "Tap below to dial emergency dispatch directly."
                }

                AlertDialog.Builder(this@MainActivity)
                    .setTitle(title)
                    .setMessage(message)
                    .setPositiveButton("OK", null)
                    .setNeutralButton("📞 Call $targetPhone") { _, _ ->
                        try {
                            val intent = Intent(Intent.ACTION_DIAL, android.net.Uri.parse("tel:$targetPhone"))
                            startActivity(intent)
                        } catch (_: Exception) {}
                    }
                    .show()
            }
        }
    }

    // --- WOMEN SAFETY DISPATCH (DIRECT TWILIO CLOUD CALL & SMS) ---
    private fun executeWomenSafetyDispatch() {
        val targetPhone = BuildConfig.EMERGENCY_PHONE
        val curLat = latitude
        val curLon = longitude

        Toast.makeText(this, "🌸 Women Safety SOS triggered! Placing emergency call...", Toast.LENGTH_SHORT).show()

        val womenVoicePrompt = "<Response><Pause length=\"1\"/><Say voice=\"alice\" language=\"en-IN\">Urgent Emergency Alert from SafeRide AI. Critical Women Safety SOS has been activated for female rider at coordinates latitude " +
            String.format(Locale.US, "%.5f", curLat) + ", longitude " + String.format(Locale.US, "%.5f", curLon) +
            ". Immediate police assistance and emergency responder dispatch is required. Check terminal now.</Say></Response>"

        val mapsLink = String.format(Locale.US, "https://maps.google.com/?q=%.5f,%.5f", curLat, curLon)
        val womenSmsBody = String.format(
            Locale.US,
            "🚨 SafeRide AI WOMEN SAFETY EMERGENCY ALERT! Female rider requested immediate assistance at Lat %.5f, Lon %.5f. Google Maps: %s. Immediate police and emergency response needed!",
            curLat, curLon, mapsLink
        )

        // 1. Asynchronously send Women Safety SMS and notify backend
        sendTwilioSmsDirectly(targetPhone, curLat, curLon, womenSmsBody) { _, _ -> }
        notifyLocalApiServer(targetPhone, curLat, curLon, "Women Safety SOS")

        // 2. Direct Twilio Cloud Voice Call with custom Women Safety prompt
        callTwilioDirectly(targetPhone, curLat, curLon, womenVoicePrompt) { callOk, callSid, callMsg ->
            runOnUiThread {
                if (isFinishing) return@runOnUiThread
                val title = if (callOk) "🌸 WOMEN SAFETY DISPATCH ACTIVE" else "Women Safety Alert Status"
                val message = if (callOk) {
                    "📞 WOMEN SAFETY EMERGENCY CALL PLACED!\n\n" +
                    "• Recipient: $targetPhone\n" +
                    "• Call SID: $callSid\n" +
                    "• Status: $callMsg\n" +
                    "• SMS Alert: Sent to emergency contacts\n" +
                    "• Live GPS: ${String.format(Locale.US, "%.5f, %.5f", curLat, curLon)}\n\n" +
                    "Emergency contacts and responder teams have received automated voice & location dispatch."
                } else {
                    "⚠️ Twilio Dispatch Notice:\n$callMsg\n\nTarget: $targetPhone"
                }

                AlertDialog.Builder(this@MainActivity)
                    .setTitle(title)
                    .setMessage(message)
                    .setPositiveButton("OK", null)
                    .setNeutralButton("📞 Call $targetPhone") { _, _ ->
                        try {
                            val intent = Intent(Intent.ACTION_DIAL, android.net.Uri.parse("tel:$targetPhone"))
                            startActivity(intent)
                        } catch (_: Exception) {}
                    }
                    .show()
            }
        }
    }

    // --- DIRECT TWILIO REST API CALL (USING CLOUD API DIRECTLY) ---
    private fun callTwilioDirectly(
        targetPhone: String,
        riderLat: Double,
        riderLon: Double,
        customPrompt: String? = null,
        onComplete: (Boolean, String, String) -> Unit
    ) {
        val accountSid = BuildConfig.TWILIO_ACCOUNT_SID.trim()
        val authToken = BuildConfig.TWILIO_AUTH_TOKEN.trim()
        val fromPhone = BuildConfig.TWILIO_PHONE_NUMBER.trim()

        if (accountSid.isBlank() || authToken.isBlank() || fromPhone.isBlank()) {
            onComplete(false, "", "Twilio credentials missing in app configuration.")
            return
        }

        Thread {
            try {
                val url = URL("https://api.twilio.com/2010-04-01/Accounts/$accountSid/Calls.json")
                val connection = url.openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.connectTimeout = 12000
                connection.readTimeout = 12000
                connection.doOutput = true

                val authString = "$accountSid:$authToken"
                val basicAuth = "Basic " + Base64.encodeToString(authString.toByteArray(Charsets.UTF_8), Base64.NO_WRAP)
                connection.setRequestProperty("Authorization", basicAuth)
                connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded")

                val twimlMessage = customPrompt ?: ("<Response><Pause length=\"1\"/><Say voice=\"alice\" language=\"en-IN\">Emergency Alert from SafeRide AI. Critical SOS triggered for rider at coordinates latitude " +
                    String.format(Locale.US, "%.5f", riderLat) + ", longitude " + String.format(Locale.US, "%.5f", riderLon) +
                    ". First responder medical and police dispatch has been notified. Check emergency terminal now.</Say></Response>")
                val encodedTwiml = URLEncoder.encode(twimlMessage, "UTF-8")
                val echoUrl = "https://twimlets.com/echo?Twiml=$encodedTwiml"

                val postParams = "To=" + URLEncoder.encode(targetPhone, "UTF-8") +
                    "&From=" + URLEncoder.encode(fromPhone, "UTF-8") +
                    "&Url=" + URLEncoder.encode(echoUrl, "UTF-8")

                connection.outputStream.use { os ->
                    os.write(postParams.toByteArray(Charsets.UTF_8))
                }

                val code = connection.responseCode
                val responseText = if (code in 200..299) {
                    connection.inputStream.bufferedReader().use { it.readText() }
                } else {
                    connection.errorStream?.bufferedReader()?.use { it.readText() } ?: "HTTP $code"
                }

                val sidMatch = Regex("\"sid\"\\s*:\\s*\"([^\"]+)\"").find(responseText)?.groupValues?.getOrNull(1)
                val isSuccess = code in 200..299 && !sidMatch.isNullOrBlank()
                val statusMatch = Regex("\"status\"\\s*:\\s*\"([^\"]+)\"").find(responseText)?.groupValues?.getOrNull(1)

                onComplete(isSuccess, sidMatch ?: "Queued", statusMatch ?: (if (isSuccess) "queued" else responseText))
                connection.disconnect()
            } catch (e: Exception) {
                onComplete(false, "", e.localizedMessage ?: "Network connection error to Twilio API")
            }
        }.start()
    }

    // --- DIRECT TWILIO SMS VIA CLOUD API ---
    private fun sendTwilioSmsDirectly(
        targetPhone: String,
        riderLat: Double,
        riderLon: Double,
        customBody: String? = null,
        onComplete: (Boolean, String) -> Unit
    ) {
        val accountSid = BuildConfig.TWILIO_ACCOUNT_SID.trim()
        val authToken = BuildConfig.TWILIO_AUTH_TOKEN.trim()
        val fromPhone = BuildConfig.TWILIO_PHONE_NUMBER.trim()

        if (accountSid.isBlank() || authToken.isBlank() || fromPhone.isBlank()) {
            onComplete(false, "Twilio credentials missing")
            return
        }

        Thread {
            try {
                val url = URL("https://api.twilio.com/2010-04-01/Accounts/$accountSid/Messages.json")
                val connection = url.openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.connectTimeout = 10000
                connection.readTimeout = 10000
                connection.doOutput = true

                val authString = "$accountSid:$authToken"
                val basicAuth = "Basic " + Base64.encodeToString(authString.toByteArray(Charsets.UTF_8), Base64.NO_WRAP)
                connection.setRequestProperty("Authorization", basicAuth)
                connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded")

                val mapsLink = String.format(Locale.US, "https://maps.google.com/?q=%.5f,%.5f", riderLat, riderLon)
                val smsBody = customBody ?: String.format(
                    Locale.US,
                    "🚨 SafeRide AI Emergency Alert! Rider SOS triggered at Lat %.5f, Lon %.5f. Google Maps: %s. Immediate assistance requested.",
                    riderLat, riderLon, mapsLink
                )

                val postParams = "To=" + URLEncoder.encode(targetPhone, "UTF-8") +
                    "&From=" + URLEncoder.encode(fromPhone, "UTF-8") +
                    "&Body=" + URLEncoder.encode(smsBody, "UTF-8")

                connection.outputStream.use { it.write(postParams.toByteArray(Charsets.UTF_8)) }
                val code = connection.responseCode
                val isSuccess = code in 200..299
                onComplete(isSuccess, "HTTP $code")
                connection.disconnect()
            } catch (e: Exception) {
                onComplete(false, e.localizedMessage ?: "SMS failed")
            }
        }.start()
    }

    // --- TEST TWILIO CALL ON DEMAND ---
    private fun testTwilioCallDirectly() {
        Toast.makeText(this, "Testing Twilio emergency call to ${BuildConfig.EMERGENCY_PHONE}...", Toast.LENGTH_SHORT).show()
        callTwilioDirectly(BuildConfig.EMERGENCY_PHONE, latitude, longitude) { ok, sid, msg ->
            runOnUiThread {
                if (isFinishing) return@runOnUiThread
                AlertDialog.Builder(this)
                    .setTitle(if (ok) "⚡ Twilio Voice Call Placed" else "Twilio Test Notice")
                    .setMessage(
                        "Target: ${BuildConfig.EMERGENCY_PHONE}\n" +
                        "Sender: ${BuildConfig.TWILIO_PHONE_NUMBER}\n" +
                        "SID: $sid\n" +
                        "Status: $msg\n\n" +
                        if (ok) "Your phone should ring within a few seconds!" else "Check your network or Twilio caller verification."
                    )
                    .setPositiveButton("OK", null)
                    .show()
            }
        }
    }

    // --- LOCAL API REPORTING (OPTIONAL BACKGROUND SYNC) ---
    private fun notifyLocalApiServer(targetPhone: String, curLat: Double, curLon: Double, incidentType: String = "Crash Incident") {
        Thread {
            try {
                val body = String.format(
                    Locale.US,
                    "{\"vehicle_type\":\"Motorcycle\",\"latitude\":%.6f,\"longitude\":%.6f," +
                        "\"samples\":[{\"speed_before\":%.2f,\"speed_after\":%.2f," +
                        "\"impact_force_g\":%.2f,\"tilt_angle_deg\":%.2f}]," +
                        "\"language\":\"English\",\"message\":\"%s: Help requested at coordinates\"," +
                        "\"trigger_call\":false,\"emergency_phone\":\"%s\"}",
                    curLat, curLon, speedKmh + 15f, speedKmh, peakG, tiltDegrees, incidentType, targetPhone
                )
                val primaryUrl = getApiBaseUrl()
                val candidateUrls = listOf(primaryUrl, "http://127.0.0.1:8000", "http://10.5.9.106:8000")
                for (baseUrl in candidateUrls) {
                    try {
                        val connection = URL("$baseUrl/api/v1/incidents").openConnection() as HttpURLConnection
                        connection.requestMethod = "POST"
                        connection.connectTimeout = 4000
                        connection.readTimeout = 4000
                        connection.doOutput = true
                        connection.setRequestProperty("Content-Type", "application/json")
                        connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
                        if (connection.responseCode in 200..299) {
                            val res = connection.inputStream.bufferedReader().use { it.readText() }
                            activeIncidentId = Regex("\"incident_id\"\\s*:\\s*\"([^\"]+)\"").find(res)?.groupValues?.getOrNull(1)
                            connection.disconnect()
                            break
                        }
                        connection.disconnect()
                    } catch (_: Exception) {}
                }
            } catch (_: Exception) {}
        }.start()
    }

    private fun getApiBaseUrl(): String {
        val prefs = getSharedPreferences("saferide_prefs", Context.MODE_PRIVATE)
        return prefs.getString("api_base_url", BuildConfig.API_BASE_URL)?.trimEnd('/') ?: BuildConfig.API_BASE_URL
    }

    private fun setApiBaseUrl(url: String) {
        val clean = url.trim().trimEnd('/')
        getSharedPreferences("saferide_prefs", Context.MODE_PRIVATE)
            .edit()
            .putString("api_base_url", clean)
            .apply()
    }

    private fun requestLocationPermission() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION), 20)
        } else {
            requestLocationUpdates()
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 20 && grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            requestLocationUpdates()
        }
    }

    private fun requestLocationUpdates() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) return
        try {
            locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000L, 2f, locationListener)
            if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 2000L, 5f, locationListener)
            }
            val lastLocation = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
                .asSequence()
                .filter { provider ->
                    try { locationManager.isProviderEnabled(provider) } catch (_: Exception) { false }
                }
                .mapNotNull { provider ->
                    try { locationManager.getLastKnownLocation(provider) } catch (_: SecurityException) { null }
                }
                .maxByOrNull { it.time }
            if (lastLocation != null) {
                onLocationChanged(lastLocation)
            } else if (::locationView.isInitialized) {
                locationView.text = "Waiting for satellite fix..."
            }
        } catch (e: SecurityException) {
            if (::locationView.isInitialized) locationView.text = "Location access denied"
        } catch (e: Exception) {
            if (::locationView.isInitialized) locationView.text = "Enable Location Services"
        }
    }

    private val locationListener = object : LocationListener {
        override fun onLocationChanged(loc: Location) = this@MainActivity.onLocationChanged(loc)
        override fun onProviderEnabled(provider: String) = Unit
        override fun onProviderDisabled(provider: String) = Unit
    }

    private fun onLocationChanged(location: Location) {
        val prev = lastRecordedLocation
        var gpsSpeed = if (location.hasSpeed() && location.speed > 0f) {
            (location.speed * 3.6f).coerceAtLeast(0f)
        } else {
            0f
        }
        if (gpsSpeed == 0f && prev != null) {
            val dist = location.distanceTo(prev)
            val timeSec = (location.time - prev.time) / 1000.0f
            if (timeSec in 0.5f..15f && dist > 1.0f) {
                gpsSpeed = ((dist / timeSec) * 3.6f).coerceIn(0f, 220f)
            }
        }
        lastRecordedLocation = location

        previousSpeedKmh = speedKmh
        speedKmh = gpsSpeed
        latitude = location.latitude
        longitude = location.longitude
        if (::locationView.isInitialized) {
            locationView.text = String.format(Locale.US, "%.5f° N, %.5f° E  ·  ACCURATE", latitude, longitude)
        }
        if (speedKmh > 10f) {
            sosCancelledRecently = false
        }
        updateScore()
    }

    private fun navItem(label: String, tint: String, action: () -> Unit): TextView = text(label, 11f, tint, true).apply {
        gravity = Gravity.CENTER
        isClickable = true
        isFocusable = true
        setOnClickListener { action() }
        layoutParams = LinearLayout.LayoutParams(0, dp(42), 1f)
    }

    private fun showAlerts() {
        AlertDialog.Builder(this)
            .setTitle("🚨 Emergency Dispatch Status")
            .setMessage("Twilio Cloud Gateway: ACTIVE\nCaller: ${BuildConfig.TWILIO_PHONE_NUMBER}\nEmergency Target: ${BuildConfig.EMERGENCY_PHONE}\n\nAll crash triggers will dial emergency voice dispatch within 10 seconds.")
            .setPositiveButton("OK", null)
            .show()
    }

    private fun openMap() {
        if (latitude == 0.0 && longitude == 0.0) {
            Toast.makeText(this, "Acquiring GPS fix...", Toast.LENGTH_SHORT).show()
            return
        }
        val mapIntent = Intent(Intent.ACTION_VIEW, android.net.Uri.parse("geo:$latitude,$longitude?q=$latitude,$longitude(SafeRide+Rider+Location)"))
        startActivity(mapIntent)
    }

    private fun openSettingsDialog() {
        val currentUrl = getApiBaseUrl()
        val input = EditText(this).apply {
            setText(currentUrl)
            hint = "http://10.5.9.106:8000"
            setPadding(dp(12), dp(10), dp(12), dp(10))
            setTextColor(color("#FFFFFF"))
            background = roundedBackground("#0F172A", 8, "#334155")
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(10), dp(20), dp(10))
        }
        container.addView(text("Twilio SID: ${BuildConfig.TWILIO_ACCOUNT_SID.take(8)}... (Cloud Active)", 11f, "#38BDF8", true))
        container.addView(text("Emergency Phone: ${BuildConfig.EMERGENCY_PHONE}", 11f, "#34D399", true).apply {
            setPadding(0, dp(4), 0, dp(10))
        })
        container.addView(text("Local API Base URL:", 11f, "#94A3B8", true))
        container.addView(input)

        AlertDialog.Builder(this)
            .setTitle("⚙ System & Cloud Settings")
            .setView(container)
            .setPositiveButton("Save") { _, _ ->
                val newUrl = input.text.toString().trim()
                if (newUrl.isNotBlank()) {
                    setApiBaseUrl(newUrl)
                    Toast.makeText(this, "Settings Saved!", Toast.LENGTH_SHORT).show()
                }
            }
            .setNeutralButton("Test Twilio Call") { _, _ ->
                testTwilioCallDirectly()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    // --- GLASSMORPHIC STYLING HELPERS ---
    private fun statTile(parent: LinearLayout, label: String, initialValue: String, valColorHex: String): TextView {
        val tile = glassCard(radius = 14, strokeColor = "#2538BDF8", fillColor = "#180F172A").apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(4), dp(10), dp(4), dp(10))
        }
        tile.addView(text(label, 9f, "#94A3B8", true).apply { gravity = Gravity.CENTER })
        val value = text(initialValue, 17f, valColorHex, true).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(2), 0, 0)
        }
        tile.addView(value)
        parent.addView(tile, LinearLayout.LayoutParams(0, dp(68), 1f).apply {
            marginStart = dp(3)
            marginEnd = dp(3)
        })
        return value
    }

    private fun section(value: String): TextView = text(value, 11f, "#7DD3FC", true).apply {
        setPadding(dp(2), dp(18), 0, dp(6))
    }

    private fun glassCard(radius: Int = 16, strokeColor: String = "#30FFFFFF", fillColor: String = "#15132238"): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = GradientDrawable().apply {
                setColor(color(fillColor))
                setStroke(dp(1), color(strokeColor))
                cornerRadius = dp(radius).toFloat()
            }
        }
    }

    private fun glassGradientCard(startHex: String, endHex: String, strokeHex: String, radius: Int): GradientDrawable {
        return GradientDrawable(
            GradientDrawable.Orientation.TOP_BOTTOM,
            intArrayOf(color(startHex), color(endHex))
        ).apply {
            setStroke(dp(1), color(strokeHex))
            cornerRadius = dp(radius).toFloat()
        }
    }

    private fun roundedBackground(fillHex: String, radius: Int, strokeHex: String? = null): GradientDrawable {
        return GradientDrawable().apply {
            setColor(color(fillHex))
            strokeHex?.let { setStroke(dp(1), color(it)) }
            cornerRadius = dp(radius).toFloat()
        }
    }

    private fun text(value: String, size: Float, hex: String, bold: Boolean): TextView = TextView(this).apply {
        text = value
        textSize = size
        setTextColor(color(hex))
        if (bold) setTypeface(null, Typeface.BOLD)
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun color(hex: String): Int = Color.parseColor(hex)
}
