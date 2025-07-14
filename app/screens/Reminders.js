import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  Switch,
  FlatList,
  TouchableOpacity,
  Modal,
  TextInput,
  Platform,
} from 'react-native';
import { Calendar } from 'react-native-calendars';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Speech from 'expo-speech';
import * as Notifications from 'expo-notifications';
import DateTimePicker from '@react-native-community/datetimepicker';
import i18n from '../i18n';

const reminderDefaults = [
  { id: '1', time: '10:00 AM', titleKey: 'irrigation', icon: '💧', enabled: true },
  { id: '2', time: '02:00 PM', titleKey: 'sowing', icon: '🌱', enabled: false },
  { id: '3', time: '05:00 PM', titleKey: 'harvesting', icon: '🌾', enabled: false },
];

const Reminders = () => {
  const navigation = useNavigation();
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [menuVisible, setMenuVisible] = useState(false);
  const [showPicker, setShowPicker] = useState(null);
  const [reminders, setReminders] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editedTitle, setEditedTitle] = useState('');
  const [langReady, setLangReady] = useState(false);

  useEffect(() => {
    const initLanguage = async () => {
      const storedLang = await AsyncStorage.getItem('appLang');
      if (storedLang) await i18n.changeLanguage(storedLang);
      setLangReady(true);
    };
    initLanguage();
  }, []);

  useEffect(() => {
    if (langReady) {
      loadReminders();
      Notifications.requestPermissionsAsync();
    }
  }, [langReady]);

  useEffect(() => {
    if (!langReady) return;
    const interval = setInterval(checkVoiceAlert, 60000);
    return () => clearInterval(interval);
  }, [reminders, langReady]);

  const loadReminders = async () => {
    try {
      const saved = await AsyncStorage.getItem('reminders');
      if (saved) {
        setReminders(JSON.parse(saved));
      } else {
        setReminders(reminderDefaults);
      }
    } catch (e) {
      console.error('Failed to load reminders:', e);
    }
  };

  const saveReminders = async (updated) => {
    setReminders(updated);
    try {
      await AsyncStorage.setItem('reminders', JSON.stringify(updated));
    } catch (e) {
      console.error('Failed to save reminders:', e);
    }
  };

  const scheduleNotification = async (reminder) => {
    const timeParts = parseTime(reminder.time);
    const now = new Date();
    const scheduleTime = new Date(now.getFullYear(), now.getMonth(), now.getDate(), timeParts.hours, timeParts.minutes);
    if (scheduleTime > now) {
      await Notifications.scheduleNotificationAsync({
        content: {
          title: i18n.t('reminders_title'),
          body: `⏰ ${reminder.title || i18n.t(reminder.titleKey)}`,
        },
        trigger: scheduleTime,
      });
    }
  };

  const parseTime = (timeStr) => {
    const [time, meridiem] = timeStr.split(' ');
    let [hours, minutes] = time.split(':').map(Number);
    if (meridiem === 'PM' && hours < 12) hours += 12;
    if (meridiem === 'AM' && hours === 12) hours = 0;
    return { hours, minutes };
  };

  const checkVoiceAlert = () => {
    const now = new Date();
    const hour = now.getHours();
    const minute = now.getMinutes();
    reminders.forEach((r) => {
      const { hours, minutes } = parseTime(r.time);
      if (r.enabled && hour === hours && minute === minutes) {
        const message = `${i18n.t('reminders_title')}: ${r.title || i18n.t(r.titleKey)}`;
        Speech.speak(message);
      }
    });
  };

  const toggleReminder = async (id) => {
    const updated = reminders.map((r) => r.id === id ? { ...r, enabled: !r.enabled } : r);
    await saveReminders(updated);
    const enabledReminder = updated.find((r) => r.id === id);
    if (enabledReminder?.enabled) scheduleNotification(enabledReminder);
  };

  const updateTime = (event, selectedDateTime) => {
    if (!selectedDateTime || !showPicker) {
      setShowPicker(null);
      return;
    }
    const newTime = formatTime(selectedDateTime);
    const updated = reminders.map((r) => r.id === showPicker ? { ...r, time: newTime } : r);
    saveReminders(updated);
    scheduleNotification(updated.find((r) => r.id === showPicker));
    setShowPicker(null);
  };

  const formatTime = (date) => {
    let hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    return `${padZero(hours)}:${padZero(minutes)} ${ampm}`;
  };

  const padZero = (n) => (n < 10 ? `0${n}` : n);

  const handleEditTitle = (id, currentTitle) => {
    setEditingId(id);
    setEditedTitle(currentTitle);
  };

  const saveEditedTitle = () => {
    const updated = reminders.map((r) => r.id === editingId ? { ...r, title: editedTitle } : r);
    saveReminders(updated);
    setEditingId(null);
    setEditedTitle('');
  };

  const menuItems = [
    { label: i18n.t('home'), route: 'Home' },
    { label: i18n.t('market_prices'), route: 'Market' },
    { label: i18n.t('weather'), route: 'Weather' },
    { label: i18n.t('reminders'), route: 'Reminders' },
    { label: i18n.t('farm_livestock'), route: 'FarmDatabase' },
    { label: i18n.t('animal_records'), route: 'AnimalRecordsScreen' },
    { label: i18n.t('govt_schemes'), route: 'GovtScheme' },
  ];

  const handleMenuPress = (route) => {
    setMenuVisible(false);
    navigation.navigate(route);
  };

  if (!langReady) return <View style={{ flex: 1, backgroundColor: '#fff' }} />;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => setMenuVisible(true)} style={styles.menuIcon}>
          <Ionicons name="menu" size={24} color="black" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{i18n.t('reminders_title')}</Text>
      </View>

      <Modal visible={menuVisible} transparent animationType="fade">
        <TouchableOpacity style={styles.menuOverlay} onPress={() => setMenuVisible(false)}>
          <View style={styles.menu}>
            {menuItems.map((item) => (
              <TouchableOpacity key={item.route} onPress={() => handleMenuPress(item.route)} style={styles.menuItem}>
                <Text style={styles.menuText}>{item.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </TouchableOpacity>
      </Modal>

      <Calendar
        current={selectedDate}
        onDayPress={(day) => setSelectedDate(day.dateString)}
        markedDates={{ [selectedDate]: { selected: true, selectedColor: '#4CAF50' } }}
        theme={{ selectedDayTextColor: '#fff', todayTextColor: '#4CAF50', arrowColor: '#4CAF50' }}
        style={styles.calendar}
      />

      <Text style={styles.subheading}>{i18n.t('tasks_on')} {selectedDate}</Text>

      <FlatList
        data={reminders}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.taskCard}>
            <Text style={styles.icon}>{item.icon}</Text>
            <View style={{ flex: 1 }}>
              {editingId === item.id ? (
                <TextInput
                  style={styles.editInput}
                  value={editedTitle}
                  onChangeText={setEditedTitle}
                  onBlur={saveEditedTitle}
                  autoFocus
                />
              ) : (
                <TouchableOpacity onLongPress={() => handleEditTitle(item.id, item.title || i18n.t(item.titleKey))}>
                  <Text style={styles.taskTitle}>{item.title || i18n.t(item.titleKey)}</Text>
                </TouchableOpacity>
              )}
              <TouchableOpacity onPress={() => setShowPicker(item.id)}>
                <Text style={styles.taskTimeText}>{item.time}</Text>
              </TouchableOpacity>
            </View>
            <Switch
              value={item.enabled}
              onValueChange={() => toggleReminder(item.id)}
              thumbColor={item.enabled ? '#4CAF50' : '#ccc'}
              trackColor={{ true: '#A5D6A7', false: '#e0e0e0' }}
            />
          </View>
        )}
      />

      {showPicker && (
        <DateTimePicker
          value={new Date()}
          mode="time"
          is24Hour={false}
          display="default"
          onChange={updateTime}
        />
      )}
    </SafeAreaView>
  );
};

export default Reminders;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 20,
    paddingTop: 40,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 50,
    position: 'relative',
    marginBottom: 10,
  },
  menuIcon: {
    position: 'absolute',
    left: 0,
    paddingHorizontal: 10,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  calendar: {
    borderRadius: 10,
    elevation: 2,
    marginBottom: 20,
  },
  subheading: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 10,
  },
  taskCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F1F8E9',
    padding: 15,
    marginBottom: 10,
    borderRadius: 10,
  },
  icon: {
    fontSize: 24,
    marginRight: 15,
  },
  taskTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  editInput: {
    fontSize: 16,
    fontWeight: '600',
    borderBottomWidth: 1,
    borderColor: '#4CAF50',
    padding: 0,
    marginBottom: 4,
  },
  taskTimeText: {
    fontSize: 14,
    color: '#4CAF50',
    textDecorationLine: 'underline',
    marginTop: 5,
  },
  menuOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.2)',
    justifyContent: 'flex-start',
    paddingTop: 60,
    paddingHorizontal: 20,
  },
  menu: {
    backgroundColor: '#fff',
    borderRadius: 10,
    elevation: 5,
    padding: 10,
  },
  menuItem: {
    paddingVertical: 10,
    paddingHorizontal: 15,
  },
  menuText: {
    fontSize: 16,
  },
});
