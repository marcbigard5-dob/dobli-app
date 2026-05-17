"""
تطبيق بسيط لاختبار بناء APK
"""
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

class DobliApp(App):
    def build(self):
        # تخطيط عمودي
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # عنوان التطبيق
        title = Label(
            text='Dobli App', 
            font_size='30sp',
            size_hint=(1, 0.3)
        )
        
        # زر
        button = Button(
            text='اضغط هنا', 
            font_size='20sp',
            size_hint=(1, 0.2),
            background_color=(0.2, 0.6, 1, 1)
        )
        
        # معلومات
        info = Label(
            text='تطبيق يعمل بنجاح',
            font_size='16sp',
            size_hint=(1, 0.3)
        )
        
        # إضافة العناصر للتخطيط
        layout.add_widget(title)
        layout.add_widget(button)
        layout.add_widget(info)
        
        # تعريف حدث الضغط على الزر
        button.bind(on_press=self.on_button_press)
        
        return layout
    
    def on_button_press(self, instance):
        instance.text = 'تم الضغط!'

if __name__ == '__main__':
    DobliApp().run()
