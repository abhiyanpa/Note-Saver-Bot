import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
from datetime import datetime, timedelta
from database import Database
from config import DATABASE_FILE
import io

db = Database(DATABASE_FILE)

def generate_analytics_report():
    """Generate comprehensive analytics report"""
    
    # Basic stats
    total_users = db.get_total_users()
    active_users_7d = db.get_active_users(7)
    active_users_30d = db.get_active_users(30)
    total_notes = db.get_total_notes_all_users()
    
    # Language distribution
    languages = db.get_language_distribution()
    
    # Note types
    note_types = db.get_notes_by_type_stats()
    
    # Top users
    top_users = db.get_top_users(10)
    
    # Retention
    retention = db.get_retention_stats()
    
    # Popular tags
    popular_tags = db.get_popular_tags_global(20)
    
    # Print report
    print("\n" + "="*60)
    print("📊 BOT ANALYTICS REPORT")
    print("="*60)
    print(f"\n👥 USER STATISTICS")
    print(f"   Total Users: {total_users}")
    print(f"   Active (7 days): {active_users_7d}")
    print(f"   Active (30 days): {active_users_30d}")
    print(f"   Activity Rate: {(active_users_7d/total_users*100):.1f}%" if total_users > 0 else "   Activity Rate: 0%")
    
    print(f"\n📝 NOTE STATISTICS")
    print(f"   Total Notes: {total_notes}")
    print(f"   Avg per User: {(total_notes/total_users):.1f}" if total_users > 0 else "   Avg per User: 0")
    
    print(f"\n📊 NOTES BY TYPE")
    for note_type, count in note_types.items():
        percentage = (count / total_notes * 100) if total_notes > 0 else 0
        print(f"   {note_type}: {count} ({percentage:.1f}%)")
    
    print(f"\n🌐 LANGUAGE DISTRIBUTION")
    for lang, count in languages.items():
        percentage = (count / total_users * 100) if total_users > 0 else 0
        print(f"   {lang}: {count} ({percentage:.1f}%)")
    
    print(f"\n🔄 RETENTION")
    print(f"   Returning Users: {retention['returning_users']}")
    print(f"   Retention Rate: {retention['retention_rate']}%")
    
    print(f"\n🏆 TOP 10 USERS")
    for i, (user_id, first_name, username, note_count) in enumerate(top_users, 1):
        username_display = f"@{username}" if username else f"ID:{user_id}"
        print(f"   {i}. {first_name} ({username_display}): {note_count} notes")
    
    print(f"\n🏷️ TOP 10 TAGS")
    for i, (tag, count) in enumerate(popular_tags[:10], 1):
        print(f"   {i}. #{tag}: {count} uses")
    
    print("\n" + "="*60 + "\n")

def generate_charts():
    """Generate analytics charts"""
    
    # User growth chart
    growth_data = db.get_user_growth_stats(30)
    if growth_data:
        dates = [row[0] for row in growth_data]
        counts = [row[1] for row in growth_data]
        
        plt.figure(figsize=(12, 6))
        plt.plot(dates, counts, marker='o', linewidth=2, markersize=6)
        plt.title('User Growth (Last 30 Days)', fontsize=16, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('New Users')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('analytics_user_growth.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✅ Saved: analytics_user_growth.png")
    
    # Daily notes chart
    notes_data = db.get_daily_notes_stats(30)
    if notes_data:
        dates = [row[0] for row in notes_data]
        counts = [row[1] for row in notes_data]
        
        plt.figure(figsize=(12, 6))
        plt.bar(dates, counts, color='#4A90E2', alpha=0.7)
        plt.title('Notes Created Per Day (Last 30 Days)', fontsize=16, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Notes Created')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig('analytics_daily_notes.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✅ Saved: analytics_daily_notes.png")
    
    # Language distribution pie chart
    languages = db.get_language_distribution()
    if languages:
        lang_names = {
            'en': 'English',
            'es': 'Español',
            'ar': 'العربية',
            'ru': 'Русский',
            'tr': 'Türkçe',
            'uz': 'O\'zbekcha'
        }
        
        labels = [lang_names.get(lang, lang) for lang in languages.keys()]
        sizes = list(languages.values())
        colors = ['#4A90E2', '#50C878', '#FFD93D', '#FF6B6B', '#9B59B6', '#3498DB']
        
        plt.figure(figsize=(10, 8))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
        plt.title('User Language Distribution', fontsize=16, fontweight='bold')
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig('analytics_languages.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✅ Saved: analytics_languages.png")
    
    # Note types pie chart
    note_types = db.get_notes_by_type_stats()
    if note_types:
        labels = list(note_types.keys())
        sizes = list(note_types.values())
        colors = ['#4A90E2', '#50C878', '#FFD93D', '#FF6B6B', '#9B59B6', '#E67E22']
        
        plt.figure(figsize=(10, 8))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
        plt.title('Notes by Content Type', fontsize=16, fontweight='bold')
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig('analytics_note_types.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✅ Saved: analytics_note_types.png")

if __name__ == '__main__':
    print("\n🔄 Generating analytics...\n")
    generate_analytics_report()
    
    print("\n📈 Generating charts...\n")
    generate_charts()
    
    print("\n✅ Analytics generation complete!\n")