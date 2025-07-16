import {
  View,
  Text,
  SafeAreaView,
  TouchableOpacity,
  TextInput,
  StyleSheet,
  FlatList,
  ListRenderItem,
  KeyboardAvoidingView,
  Platform,
  Image,
  Keyboard,
  ActivityIndicator,
  Modal,
  PanResponder,
} from 'react-native';
import React, { useEffect, useRef, useState } from 'react';
import { useLocalSearchParams, useNavigation } from 'expo-router';
import { useConvex, useMutation, useQuery } from 'convex/react';
import { api } from '../../convex/_generated/api';
import { Doc, Id } from '@/convex/_generated/dataModel';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { Audio } from 'expo-av';

const Page = () => {
  const { chatid } = useLocalSearchParams();
  const [newMessage, setNewMessage] = useState('');
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [showRecordingModal, setShowRecordingModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [user, setUser] = useState<string | null>(null);
  const listRef = useRef<FlatList>(null);
  const convex = useConvex();
  const navigation = useNavigation();
  const addMessage = useMutation(api.message.sendMessage);
  const messages = useQuery(api.message.get, { chatId: chatid as Id<'groups'> }) || [];
  const [slideCanceled, setSlideCanceled] = useState(false);

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onPanResponderMove: (_, gesture) => {
        if (gesture.dx < -50) {
          setSlideCanceled(true);
          setShowRecordingModal(false);
        }
      },
      onPanResponderRelease: () => {
        if (!slideCanceled) stopRecording();
        else setSlideCanceled(false);
      },
    })
  ).current;

  useEffect(() => {
    const loadUser = async () => {
      const u = await AsyncStorage.getItem('user');
      setUser(u);
    };
    loadUser();
  }, []);

  useEffect(() => {
    const loadGroup = async () => {
      const groupInfo = await convex.query(api.groups.getGroup, { id: chatid as Id<'groups'> });
      navigation.setOptions({ headerTitle: groupInfo?.name });
    };
    loadGroup();
  }, [chatid]);

  useEffect(() => {
    setTimeout(() => {
      listRef.current?.scrollToEnd({ animated: true });
    }, 300);
  }, [messages]);

  const handleSendMessage = async () => {
    Keyboard.dismiss();
    if (selectedImage) {
      const blob = await (await fetch(selectedImage)).blob();
      const url = `${process.env.EXPO_PUBLIC_CONVEX_SITE}/sendImage?user=${encodeURIComponent(user!)}&group_id=${chatid}&content=${encodeURIComponent(newMessage)}`;
      setUploading(true);
      await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': blob.type },
        body: blob,
      });
      setSelectedImage(null);
      setNewMessage('');
      setUploading(false);
    } else if (newMessage.trim()) {
      await addMessage({
        group_id: chatid as Id<'groups'>,
        content: newMessage,
        user: user || 'Anonymous',
      });
      setNewMessage('');
    }
  };

  const captureImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 1 });
    if (!result.canceled) setSelectedImage(result.assets[0].uri);
  };

  const startRecording = async () => {
    try {
      const { granted } = await Audio.requestPermissionsAsync();
      if (!granted) return alert('Mic permission needed');
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      setRecording(recording);
      setShowRecordingModal(true);
    } catch (err) {
      console.error('Recording start error:', err);
    }
  };

  const stopRecording = async () => {
    try {
      setShowRecordingModal(false);
      await recording?.stopAndUnloadAsync();
      const uri = recording?.getURI();
      setRecording(null);
      if (!uri) return;
      const blob = await (await fetch(uri)).blob();
      setUploading(true);
      const url = `${process.env.EXPO_PUBLIC_CONVEX_SITE}/sendAudio?user=${encodeURIComponent(user!)}&group_id=${chatid}&content=Audio`;
      await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': blob.type },
        body: blob,
      });
    } catch (err) {
      console.error('Stop recording error:', err);
    } finally {
      setUploading(false);
    }
  };

  const playAudio = async (uri: string) => {
    const { sound } = await Audio.Sound.createAsync({ uri });
    await sound.playAsync();
  };

  const renderMessage: ListRenderItem<Doc> = ({ item }) => {
    const isUserMessage = item.user === user;
    const isAudio = item.file && item.content === 'Audio';

    return (
      <View style={[styles.messageContainer, isUserMessage ? styles.userMessageContainer : styles.otherMessageContainer]}>
        {item.content !== 'Audio' && <Text style={[styles.messageText, isUserMessage && styles.userMessageText]}>{item.content}</Text>}
        {item.file && (
          isAudio ? (
            <TouchableOpacity onPress={() => playAudio(item.file!)}>
              <Ionicons name="play-circle" size={36} color={isUserMessage ? '#fff' : '#000'} />
            </TouchableOpacity>
          ) : (
            <Image source={{ uri: item.file }} style={styles.media} />
          )
        )}
        <Text style={styles.timestamp}>
          {new Date(item._creationTime).toLocaleTimeString()} - {item.user}
        </Text>
      </View>
    );
  };

  const isSendEnabled = newMessage.trim().length > 0 || selectedImage;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#fff' }}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={100}
      >
        <FlatList
          ref={listRef}
          data={messages}
          renderItem={renderMessage}
          keyExtractor={(item) => item._id.toString()}
          ListFooterComponent={<View style={{ paddingBottom: 100 }} />}
        />

        <View style={styles.inputContainer}>
          {selectedImage && (
            <Image source={{ uri: selectedImage }} style={styles.media} />
          )}
          <View style={styles.inputRow}>
            <TextInput
              style={styles.textInput}
              value={newMessage}
              onChangeText={setNewMessage}
              placeholder="Type your message"
              multiline
            />
            <TouchableOpacity style={styles.sendButton} onPress={captureImage}>
              <Ionicons name="image-outline" style={styles.sendButtonText} />
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.sendButton}
              {...panResponder.panHandlers}
              onLongPress={startRecording}
              onPressOut={() => {
                if (!slideCanceled) stopRecording();
                else setSlideCanceled(false);
              }}
            >
              <Ionicons name="mic-outline" style={styles.sendButtonText} />
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.sendButton, { opacity: isSendEnabled ? 1 : 0.4 }]}
              onPress={handleSendMessage}
              disabled={!isSendEnabled}
            >
              <Ionicons name="send-outline" style={styles.sendButtonText} />
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>

      <Modal transparent visible={showRecordingModal}>
        <View style={styles.recordingModal}>
          <Ionicons name="mic" size={48} color="#fff" />
          <Text style={{ color: 'white', marginTop: 10 }}>
            {slideCanceled ? 'Recording Canceled' : 'Recording...'}
          </Text>
        </View>
      </Modal>

      {uploading && (
        <View style={styles.uploadingOverlay}>
          <ActivityIndicator color="#fff" size="large" />
        </View>
      )}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8F5EA' },
  inputContainer: {
    padding: 10,
    backgroundColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -8 },
    shadowOpacity: 0.1,
    shadowRadius: 5,
    elevation: 3,
    position: 'absolute',
    bottom: 10,
    width: '100%',
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  textInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: 'gray',
    borderRadius: 5,
    paddingHorizontal: 10,
    minHeight: 40,
    backgroundColor: '#fff',
    paddingTop: 10,
  },
  sendButton: {
    backgroundColor: '#62b667',
    borderRadius: 5,
    padding: 10,
    marginLeft: 10,
    alignSelf: 'flex-end',
  },
  sendButtonText: {
    color: 'white',
    fontSize: 20,
    fontWeight: 'bold',
  },
  messageContainer: {
    padding: 10,
    borderRadius: 10,
    marginTop: 10,
    marginHorizontal: 10,
    maxWidth: '80%',
  },
  userMessageContainer: {
    backgroundColor: '#597f57ff',
    alignSelf: 'flex-end',
  },
  otherMessageContainer: {
    alignSelf: 'flex-start',
    backgroundColor: '#fff',
  },
  messageText: { fontSize: 16 },
  userMessageText: { color: '#fff' },
  timestamp: {
    fontSize: 12,
    color: '#c7c7c7',
  },
  media: {
    width: 200,
    height: 200,
    margin: 10,
    borderRadius: 10,
  },
  uploadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.4)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  recordingModal: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.6)',
    alignItems: 'center',
    justifyContent: 'center',
  },
});

export default Page;
