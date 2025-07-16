import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Linking,
  ScrollView,
} from 'react-native';
import {
  Ionicons,
  MaterialIcons,
  FontAwesome5,
  Entypo,
  FontAwesome,
} from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import i18n from '../i18n';

const Home = () => {
  const navigation = useNavigation();

  const features = [
    {
      title: i18n.t('weather'),
      subtitle: i18n.t('weather_sub'),
      iconComponent: Ionicons,
      iconProps: { name: 'sunny-outline', size: 24, color: 'black' },
      screen: 'Weather',
    },
    {
      title: i18n.t('crop_advisory'),
      subtitle: i18n.t('crop_advisory_sub'),
      iconComponent: MaterialIcons,
      iconProps: { name: 'eco', size: 24, color: 'black' },
      screen: 'CropAdvice',
    },
    {
      title: i18n.t('market_prices'),
      subtitle: i18n.t('market_prices_sub'),
      iconComponent: FontAwesome5,
      iconProps: { name: 'rupee-sign', size: 20, color: 'black' },
      screen: 'Market',
    },
    {
      title: i18n.t('ask_kisanvaani'),
      subtitle: i18n.t('ask_kisanvaani_sub'),
      iconComponent: Ionicons,
      iconProps: { name: 'chatbubble-ellipses-outline', size: 22, color: 'black' },
      screen: 'VoiceAssistant',
    },
    {
      title: i18n.t('community'),
      subtitle: i18n.t('community_sub'),
      iconComponent: Ionicons,
      iconProps: { name: 'people-outline', size: 24, color: 'black' },
      screen: '',
    },
    {
      title: i18n.t('help'),
      subtitle: i18n.t('help_sub'),
      iconComponent: Entypo,
      iconProps: { name: 'help-with-circle', size: 22, color: 'black' },
      screen: 'Help',
    },
    {
      title: i18n.t('farm_livestock'),
      subtitle: i18n.t('livestock_db_sub'),
      iconComponent: FontAwesome5,
      iconProps: { name: 'horse', size: 22, color: 'black' },
      screen: 'FarmDatabase',
    },
    {
      title: i18n.t('govt_schemes'),
      subtitle: i18n.t('govt_schemes_sub'),
      iconComponent: FontAwesome,
      iconProps: { name: 'institution', size: 22, color: 'black' },
      screen: 'GovtScheme',
    },
    {
      title: i18n.t('reminders'),
      subtitle: i18n.t('reminders_sub'),
      iconComponent: Ionicons,
      iconProps: { name: 'alarm-outline', size: 22, color: 'black' },
      screen: 'Reminders',
    },
  ];

  const handlePress = (item) => {
    if (item.screen === 'VoiceAssistant') {
      Linking.openURL('https://jnmrg673-8501.inc1.devtunnels.ms/');
    } else if (item.screen) {
      navigation.navigate(item.screen);
    } else {
      console.log(`${item.title} pressed`);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>{i18n.t('kisanvaani')}</Text>
        <Text style={styles.greeting}>{i18n.t('welcome_short')}</Text>

        <View style={styles.grid}>
          {features.map((item, idx) => {
            const Icon = item.iconComponent;
            return (
              <TouchableOpacity key={idx} style={styles.card} onPress={() => handlePress(item)}>
                <Icon {...item.iconProps} />
                <Text style={styles.cardTitle}>{item.title}</Text>
                <Text style={styles.cardSubtitle}>{item.subtitle}</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </ScrollView>

      {/* Mic Button opens external link */}
      <TouchableOpacity
        style={styles.micButton}
        onPress={() => Linking.openURL('https://jnmrg673-8501.inc1.devtunnels.ms/')}
      >
        <Ionicons name="mic" size={28} color="#fff" />
      </TouchableOpacity>
    </SafeAreaView>
  );
};

export default Home;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  scroll: {
    paddingTop: 40,
    paddingBottom: 100,
    paddingHorizontal: 20,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    color: '#111',
  },
  greeting: {
    fontSize: 26,
    fontWeight: 'bold',
    marginVertical: 20,
    color: '#222',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  card: {
    width: '47%',
    backgroundColor: '#F5F8F2',
    borderRadius: 12,
    padding: 15,
    marginBottom: 20,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginTop: 10,
  },
  cardSubtitle: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  micButton: {
    position: 'absolute',
    bottom: 30,
    right: 30,
    backgroundColor: '#3CB043',
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 5,
  },
});
