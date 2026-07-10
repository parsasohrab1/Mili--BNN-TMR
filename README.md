
تراشه شتاب‌دهنده BNN با معماری سیستولیک + TMR
Edge AI Accelerator Chip with Systolic Array + TMR
1. مقدمه (Introduction)
1.1 هدف (Purpose)
این سند مشخصات کامل سیستم را برای تراشه شتاب‌دهنده هوش مصنوعی لبه‌ای با معماری ماتریس سیستولیک و مقاوم‌سازی سه‌گانه (TMR) در برابر خطاهای نرم تشریح می‌کند. هدف اصلی، طراحی تراشه‌ای کم‌مصرف (توان کمتر از ۵۰ وات) با کارایی بالا برای اجرای شبکه‌های عصبی باینری (BNN) در سامانه‌های هوایی خودگردان است.

1.2 محدوده (Scope)
طراحی تراشه ASIC ۱۴ نانومتری

پشتیبانی از شبکه‌های عصبی باینری (۱-بیت) با عمق تا ۲۰ لایه

مقاوم‌سازی در برابر خطاهای نرم (SEU) با روش TMR

رابط‌های ارتباطی: PCIe Gen4, SPI, I2C, UART

مصرف توان هدف: < ۵۰ وات

دمای عملیاتی: -۴۰°C تا +۸۵°C

1.3 اصطلاحات و اختصارات (Definitions & Acronyms)
اختصار	توضیح
BNN	Binary Neural Network - شبکه عصبی با وزن‌های ۱-بیتی
TMR	Triple Modular Redundancy - افزونگی مدولار سه‌گانه
SEU	Single Event Upset - خطای نرم ناشی از تشعشع
TOPS	Tera Operations Per Second - ترا عملیات در ثانیه
ASIC	Application-Specific Integrated Circuit
2. الزامات کلی (Overall Description)
2.1 پرسپکتیو محصول (Product Perspective)
این تراشه به عنوان شتاب‌دهنده تخصصی در کنار پردازنده اصلی (STM32H7) قرار می‌گیرد و وظیفه اجرای الگوریتم‌های سنگین بینایی ماشین و یادگیری عمیق را بر عهده دارد.

text
┌─────────────────────────────────────────────┐
│           پردازنده اصلی (STM32H7)           │
│  کنترل پرواز، فیوژن حسگر، ارتباطات          │
└──────────────┬──────────────────────────────┘
               │ PCIe/SPI
┌──────────────▼──────────────────────────────┐
│     تراشه شتاب‌دهنده BNN (ASIC)            │
│  • معماری سیستولیک                         │
│  • TMR برای مقاوم‌سازی                     │
│  • توان < ۵۰ وات                           │
└─────────────────────────────────────────────┘
2.2 ویژگی‌های اصلی (Product Functions)
اجرای شبکه BNN: پشتیبانی از مدل‌های پیش‌آموزش‌دیده با دقت > ۹۵٪

مقاوم‌سازی TMR: تصحیح خطا در سه ماژول موازی با رأی‌گیری اکثریت

پردازش بلادرنگ: تأخیر کمتر از ۱۰ میلی‌ثانیه برای هر تصویر

مدیریت توان: قابلیت تنظیم فرکانس و ولتاژ دینامیک

2.3 کاربران (User Characteristics)
مهندسان سخت‌افزار: برای یکپارچه‌سازی و تست

مهندسان نرم‌افزار: برای توسعه درایور و API

توسعه‌دهندگان الگوریتم: برای پیاده‌سازی مدل‌های عصبی

3. الزامات سیستم (System Requirements)
3.1 الزامات سخت‌افزاری (Hardware Requirements)
پارامتر	مقدار	توضیح
تکنولوژی ساخت	۱۴ نانومتری FinFET	
ولتاژ کاری	۰.۸۵V - ۱.۲V	قابل تنظیم
فرکانس پایه	۴۰۰ MHz	قابل اسکیل تا ۸۰۰ MHz
حافظه داخلی	۳۲ MB SRAM	با ECC
پهنای باند حافظه	۲۵۶ بیت	
تعداد هسته‌ها	۶۴ PE (Processing Element)	آرایه ۸×۸
توان مصرفی	< ۵۰ وات	Typical: ۳۰ وات
بسته‌بندی	BGA-484	
3.2 الزامات نرم‌افزاری (Software Requirements)
ویژگی	الزام
سیستم‌عامل پشتیبانی‌شده	Linux RT, Zephyr, FreeRTOS
درایور	PCIe/SPI با پشتیبانی DMA
API سطح بالا	Python/C++ برای بارگذاری مدل
پشتیبانی از فرمت‌ها	ONNX, TensorFlow Lite, PyTorch
ابزارهای توسعه	کامپایلر/بهینه‌ساز مدل
4. مشخصات عملکردی (Functional Requirements)
4.1 FR-1: استنتاج شبکه عصبی باینری
توضیح: تراشه باید بتواند یک شبکه عصبی باینری با وزن‌های ۱-بیتی را در زمان واقعی اجرا کند.

ورودی:

تصویر یا ویژگی‌های استخراج‌شده (اندازه متغیر: ۳۲×۳۲ تا ۲۲۴×۲۲۴)

وزن‌های شبکه (ذخیره شده در حافظه داخلی)

خروجی:

نتیجه طبقه‌بندی یا شناسایی

بردار ویژگی‌های استخراج‌شده

معیار پذیرش:

دقت ≥ ۹۵% نسبت به نسخه float

تأخیر < ۱۰ms برای تصویر ۲۲۴×۲۲۴

مصرف انرژی < ۲mJ به ازای هر استنتاج

4.2 FR-2: مقاوم‌سازی در برابر خطا (TMR)
توضیح: سیستم باید با استفاده از افزونگی سه‌گانه، خطاهای نرم را تصحیح کند.

ورودی:

سه ماژول محاسباتی موازی

داده‌های ورودی یکسان

خروجی:

خروجی اکثریت رأی‌گیری‌شده

معیار پذیرش:

تشخیص و تصحیح ≥ ۹۹% از خطاهای SEU

تأخیر اضافی TMR < ۵%

افزایش توان < ۱۵%

4.3 FR-3: مدیریت توان پویا (Dynamic Power Management)
توضیح: تراشه باید بتواند فرکانس و ولتاژ را بر اساس بار کاری تنظیم کند.

حالت‌های توان:

حالت	فرکانس	توان مصرفی	زمان فعال‌سازی
Sleep	۰ MHz	< ۱۰mW	< ۱μs
Idle	۱۰۰ MHz	۵W	< ۵۰μs
Normal	۴۰۰ MHz	۳۰W	پایه
Turbo	۸۰۰ MHz	۴۸W	< ۱۰۰μs
معیار پذیرش:

زمان سوئیچ بین حالت‌ها < ۱۰۰μs

کاهش توان حداقل ۴۰% در حالت Idle

5. کد تولید داده - محصول اول
python
# =====================================================
# SRS - PRODUCT 1: EDGE AI CHIP WITH BNN + TMR
# Data Generation Script
# =====================================================

import numpy as np
import pandas as pd
from datetime import datetime

np.random.seed(42)

def generate_chip_benchmark_data():
    """
    تولید داده‌های معیار عملکرد تراشه بر اساس SRS
    شامل ۴ سناریو: عادی، تنش حرارتی، تشعشع، لرزش بالا
    """
    
    chip_data = []
    scenarios = ['nominal', 'thermal_stress', 'radiation_SEU', 'high_vibration']
    batch_sizes = [1, 4, 16, 64]
    frequencies = [100, 200, 400, 800]  # MHz
    temperatures = [25, 50, 75, 85]  # درجه سانتی‌گراد
    
    for scenario in scenarios:
        for batch in batch_sizes:
            for freq in frequencies:
                # ========== محاسبه توان مصرفی ==========
                # فرمول: P = P0 + α*f + β*T + γ*error_rate
                base_power = 5.0 + (freq / 100) * 2.5  # وات
                
                if scenario == 'nominal':
                    power = base_power + np.random.normal(0, 0.5)
                elif scenario == 'thermal_stress':
                    temp_factor = 1 + (temperatures[batch_sizes.index(batch) % 4] - 25) * 0.008
                    power = base_power * temp_factor + np.random.normal(0, 0.3)
                elif scenario == 'radiation_SEU':
                    # افزایش توان به دلیل TMR فعال
                    power = base_power * 1.15 + np.random.normal(0, 0.2)
                else:  # high_vibration
                    power = base_power * 1.1 + np.random.normal(0, 0.4)
                
                power = max(0.1, round(power, 2))
                
                # ========== محاسبه تأخیر ==========
                # Latency = L0 + (batch/freq) * K
                base_latency = (batch ** 0.3) * (1000 / freq) * 2
                if scenario == 'thermal_stress':
                    latency = base_latency * 1.25
                elif scenario == 'radiation_SEU':
                    latency = base_latency * 1.05
                elif scenario == 'high_vibration':
                    latency = base_latency * 1.15
                else:
                    latency = base_latency
                
                latency = round(latency + np.random.normal(0, 0.1), 2)
                
                # ========== محاسبه TOPS/W ==========
                # TOPS/W = (TOPS) / Power
                tops = 64.0 * (freq / 400) * (1 - 0.01 * (batch - 1))
                if scenario == 'thermal_stress':
                    tops *= 0.75
                elif scenario == 'radiation_SEU':
                    tops *= 0.85
                elif scenario == 'high_vibration':
                    tops *= 0.90
                
                tops_per_watt = round(tops / power if power > 0 else 0, 2)
                
                # ========== محاسبه دقت ==========
                # Accuracy = 97% - degradation
                base_accuracy = 97.5 - (batch ** 0.2) * 0.3
                if scenario == 'radiation_SEU':
                    accuracy = base_accuracy * 0.88
                elif scenario == 'thermal_stress':
                    accuracy = base_accuracy * 0.95
                else:
                    accuracy = base_accuracy
                
                accuracy = round(accuracy + np.random.normal(0, 0.2), 2)
                accuracy = min(99.5, max(80.0, accuracy))
                
                # ========== اثرگذاری TMR ==========
                tmr_effectiveness = 99.5 if scenario != 'radiation_SEU' else 92.0 + np.random.normal(0, 1)
                tmr_effectiveness = round(min(100, max(85, tmr_effectiveness)), 2)
                
                # ========== انرژی مصرفی هر استنتاج ==========
                energy_per_inference = round((power * latency) / 1000, 4)
                
                chip_data.append({
                    'scenario': scenario,
                    'batch_size': batch,
                    'frequency_mhz': freq,
                    'temperature_c': temperatures[batch_sizes.index(batch) % 4],
                    'power_watts': power,
                    'latency_ms': latency,
                    'tops_per_watt': tops_per_watt,
                    'accuracy_pct': accuracy,
                    'tmr_effectiveness_pct': tmr_effectiveness,
                    'energy_per_inference_mj': energy_per_inference,
                    'meets_spec': 'YES' if (
                        power < 50 and 
                        latency < 10 and 
                        accuracy > 95 and 
                        tmr_effectiveness > 90
                    ) else 'NO'
                })
    
    return pd.DataFrame(chip_data)

# ========== تولید و ذخیره داده ==========
print("🚀 Generating Product 1 (Edge AI Chip) benchmark data...")
df_chip = generate_chip_benchmark_data()
df_chip.to_csv('edge_ai_chip_benchmark.csv', index=False)

# ========== گزارش آماری ==========
print("\n" + "="*60)
print("PRODUCT 1 - EDGE AI CHIP BENCHMARK SUMMARY")
print("="*60)
print(f"Total records: {len(df_chip)}")
print(f"Scenarios: {df_chip['scenario'].unique().tolist()}")
print(f"Batch sizes: {sorted(df_chip['batch_size'].unique().tolist())}")
print(f"Frequency range: {df_chip['frequency_mhz'].min()} - {df_chip['frequency_mhz'].max()} MHz")

print("\n--- Performance by Scenario ---")
summary = df_chip.groupby('scenario').agg({
    'power_watts': 'mean',
    'latency_ms': 'mean',
    'tops_per_watt': 'mean',
    'accuracy_pct': 'mean',
    'tmr_effectiveness_pct': 'mean'
}).round(2)
print(summary)

print(f"\n✅ Compliance rate: {df_chip['meets_spec'].value_counts(normalize=True)['YES']*100:.1f}%")

print("\n📁 File saved: edge_ai_chip_benchmark.csv")
print("\n✅ Product 1 data generation complete!")
