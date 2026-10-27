plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "org.jarrellcodex"
    compileSdk = 34

    defaultConfig {
        applicationId = "org.jarrellcodex"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"
    }

    // The databases ship gzipped inside the app and are expanded into app
    // storage on first launch: codex 132 MB -> 456 MB, and the optional
    // commentary 48 MB -> 148 MB. No asset pack, no first-run download: the
    // app works the moment it is installed, which is the whole point.
    //
    // The extension is .gzip, NOT .gz, and that is deliberate. AAPT
    // special-cases a ".gz" asset: it strips the extension and re-packs the
    // contents, so "codex.db.gz" lands in the APK as "codex.db" holding the
    // DECOMPRESSED database. The app would then look for an asset that is not
    // there, and the APK would be 32 MB larger for the privilege, because
    // AAPT's deflate is worse than gzip -9. ".gzip" is not special-cased, and
    // noCompress keeps it stored byte-for-byte as built.
    //
    // Size: Play allows a 500 MB compressed download for an app bundle's base
    // module, which this is inside. A plain APK is capped at 100 MB, so the
    // Play build must be an .aab (bundleRelease). The APK is for sideloading,
    // where no limit applies.
    // WebP is already compressed, so deflating it again costs build time
    // and decode time and saves nothing. Stored, it also means a picture can
    // be decoded straight from the asset stream without being copied out
    // first, which is how Pictures.kt reads all 457 of them.
    androidResources {
        noCompress += listOf("gzip", "webp")
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    // Sideloaded builds must be signed with the SAME key every release, or
    // existing installs cannot update and users lose their notes.
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { compose = true }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.vm)
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.tooling)
    implementation(libs.compose.material3)
}
