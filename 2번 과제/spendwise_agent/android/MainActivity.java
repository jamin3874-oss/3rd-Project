package io.github.jamin3874.spendwise;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.widget.Toast;

/** Opens the hosted ledger in a browser-managed Custom Tab with its persistent cookies. */
public final class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        Uri ledger = Uri.parse("https://spendwise-f6d6d.onrender.com/");
        Intent openLedger = new Intent(Intent.ACTION_VIEW, ledger);
        Bundle options = new Bundle();
        options.putBinder("android.support.customtabs.extra.SESSION", null);
        options.putInt("android.support.customtabs.extra.TOOLBAR_COLOR", Color.rgb(25, 75, 63));
        openLedger.putExtras(options);
        try {
            startActivity(openLedger);
        } catch (ActivityNotFoundException unavailable) {
            Toast.makeText(this, "가계부를 열 수 있는 웹 브라우저를 설치해 주세요.", Toast.LENGTH_LONG).show();
        } finally {
            finish();
        }
    }
}
