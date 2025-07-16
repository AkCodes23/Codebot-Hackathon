import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import * as Speech from 'expo-speech';
import { useRoute, useNavigation } from '@react-navigation/native';
import i18n from '../i18n';

export default function WelcomeScreen() {
  const route = useRoute();
  const navigation = useNavigation();
  const { selectedLang = 'en' } = route.params || {};

  const [displayedText, setDisplayedText] = useState('');
  const [speechDone, setSpeechDone] = useState(false);

  useEffect(() => {
    i18n.changeLanguage(selectedLang);
    const fullText = i18n.t('welcome');

    // Start text-to-speech
    Speech.speak(fullText, {
      language: selectedLang,
      onDone: () => {
        setSpeechDone(true);
        navigation.replace('Home');
      },
    });

    // Typing effect
    let currentIndex = 0;
    const interval = setInterval(() => {
      setDisplayedText(fullText.slice(0, currentIndex + 1));
      currentIndex++;
      if (currentIndex === fullText.length) {
        clearInterval(interval);
      }
    }, 50);

    return () => {
      Speech.stop();
      clearInterval(interval);
    };
  }, [selectedLang]);

  const handleSkip = () => {
    Speech.stop();
    navigation.replace('Home');
  };

  return (
    <View style={styles.container}>
      <Text style={styles.text}>{displayedText}</Text>
      <TouchableOpacity onPress={handleSkip} style={styles.skipButton}>
        <Text style={styles.skipText}>{i18n.t('skip') || 'Skip'}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#bad2ab',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 30,
  },
  text: {
    fontSize: 24,
    color: '#124936',
    textAlign: 'center',
    fontWeight: '500',
    lineHeight: 36,
  },
  skipButton: {
    marginTop: 30,
    backgroundColor: '#124936',
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  skipText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
